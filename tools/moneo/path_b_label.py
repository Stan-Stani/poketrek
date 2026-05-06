#!/usr/bin/env python3
"""Path B step 2: For each (page, idx) whose blit-computed fp appears in
captured live VRAM groups, find the (frame, line, pos) on screen, OCR that
16x16 region from the matching FB, and emit (page, idx) -> char.

Cross-validate against tools/moneo/glyph-map.json verified entries.
"""
from __future__ import annotations
import hashlib, json, struct, subprocess, tempfile, os, re
from pathlib import Path
from collections import defaultdict, Counter
from PIL import Image
from concurrent.futures import ProcessPoolExecutor, as_completed

ROM = bytes(Path("Pocket Monsters - LeafGreen (Korean).gba").read_bytes())
IWRAM = bytes(Path(".moneo-artifacts/dumps/iwram.bin").read_bytes())
FONT_BASE = 0x780000
table1 = ROM[0x1CDF1C : 0x1CDF1C + 256]
table2 = struct.unpack_from("<256H", IWRAM, 0x0A40)


def blit_tile_v(rom_off):
    out = bytearray(32)
    for hw in range(8):
        b0 = ROM[rom_off + hw*2]; b1 = ROM[rom_off + hw*2 + 1]
        v0 = table2[table1[b0]]; v1 = table2[table1[b1]]
        out[hw*4+0] = v0 & 0xFF; out[hw*4+1] = (v0>>8)&0xFF
        out[hw*4+2] = v1 & 0xFF; out[hw*4+3] = (v1>>8)&0xFF
    return bytes(out)


def glyph_fp4(p, i):
    base = FONT_BASE + p*0x2000 + i*32
    parts = [blit_tile_v(base+o) for o in (0, 16, 256, 272)]
    return hashlib.sha256(b"".join(parts)).hexdigest()[:16]


# Screen coord -> framebuffer pixel: line k -> top row TEXT_ROW_TOPS[k]*8 px
TEXT_ROW_TOPS = [3, 5, 7, 10, 12, 15, 17]


def ocr_region(img, x_tile, y_tile):
    """OCR a 16x16 region (2x2 tiles) at given screen tile coords."""
    x0 = x_tile * 8; y0 = y_tile * 8
    region = img.crop((x0, y0, x0 + 16, y0 + 16)).convert('L')
    big = region.resize((128, 128), Image.LANCZOS)
    # Add white border
    pad = Image.new('L', (160, 160), 255)
    pad.paste(big, (16, 16))
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tf:
        pad.save(tf.name); tmp = tf.name
    try:
        out = subprocess.run(['tesseract', tmp, '-', '-l', 'kor', '--psm', '10'],
                             capture_output=True, text=True, timeout=10)
        text = out.stdout.strip()
        for c in text:
            if '\uAC00' <= c <= '\uD7A3':
                return c
        return None
    finally:
        os.unlink(tmp)


def find_fb_for_frame(frame, fb_dir):
    fbs = sorted(Path(fb_dir).glob('fb-*.bin'))
    for fp in fbs:
        m = re.search(r'(\d+)\.bin$', fp.name)
        if not m: continue
        f = int(m.group(1))
        if f >= frame and f - frame < 100:
            return fp
    return None


def process_one(args):
    pi, fp4, group, fb_path = args
    if not fb_path or not fb_path.exists():
        return pi, None
    img = Image.frombytes('RGBA', (240, 160), fb_path.read_bytes())
    line = group['line']
    pos = group['pos']
    top = TEXT_ROW_TOPS[line]
    # Korean text columns: each char is 2 tiles wide; capture starts at first
    # nonzero col on row "top"; we need that start to find the char column.
    # Approximation: just OCR the entire row strip and let positional alignment
    # downstream figure out which char this is. Simpler fallback: OCR the row
    # text and use position index directly assuming start col ~= 1.
    # For now: take the whole text-area row and OCR, return all hangul chars.
    region = img.crop((0, top*8, 240, (top+2)*8)).convert('L')
    big = region.resize((240*4, 16*4), Image.LANCZOS)
    pad = Image.new('L', (240*4 + 32, 16*4 + 32), 255)
    pad.paste(big, (16, 16))
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tf:
        pad.save(tf.name); tmp = tf.name
    try:
        out = subprocess.run(['tesseract', tmp, '-', '-l', 'kor', '--psm', '7'],
                             capture_output=True, text=True, timeout=10)
        chars = [c for c in out.stdout if '\uAC00' <= c <= '\uD7A3']
        if pos < len(chars):
            return pi, chars[pos]
        return pi, None
    finally:
        os.unlink(tmp)


def main():
    cap_path = '.moneo-artifacts/capture-walk.json'
    fb_dir = Path('.moneo-artifacts/dumps/fb-walk')
    cap = json.load(open(cap_path))
    groups = cap['groups']

    # Compute fp -> (page, idx) for all glyphs
    pi_fps = {}
    for p in range(1, 7):
        for i in range(256):
            pi_fps[(p, i)] = glyph_fp4(p, i)
    fp_to_pi = {fp: pi for pi, fp in pi_fps.items()}

    # Find groups whose fps[0] (charblock 0, where font lives) matches a (page, idx)
    matches = []  # (pi, fp, group)
    for g in groups:
        for cb_fp in g['fps']:
            if cb_fp in fp_to_pi:
                matches.append((fp_to_pi[cb_fp], cb_fp, g))
                break
    print(f"matched groups: {len(matches)}")
    pi_set = set(pi for pi, _, _ in matches)
    print(f"unique (page, idx) matched: {len(pi_set)}")

    # Pair each match with its FB
    args = []
    for pi, fp, g in matches:
        fb = find_fb_for_frame(g['frame'], fb_dir)
        args.append((pi, fp, g, fb))
    print(f"matches with FB available: {sum(1 for a in args if a[3])}")

    # OCR
    votes = defaultdict(Counter)
    with ProcessPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(process_one, a) for a in args[:2000]]  # cap workload
        for i, fut in enumerate(as_completed(futs)):
            pi, ch = fut.result()
            if ch:
                votes[pi][ch] += 1
            if (i+1) % 200 == 0:
                print(f"  ocr {i+1}/{len(futs)}")

    print(f"\n(page, idx) with at least 1 OCR vote: {len(votes)}")

    # Build map
    map_out = {}; conf = {}
    for pi, c in votes.items():
        ch, n = c.most_common(1)[0]
        total = sum(c.values())
        if n >= 2 and n/total >= 0.5:
            map_out[f"F{pi[0]},{pi[1]}"] = ch
            conf[f"F{pi[0]},{pi[1]}"] = n/total

    print(f"high-conf path-B entries: {len(map_out)}")

    # Compare with verified glyph-map.json
    verified = json.load(open('tools/moneo/glyph-map.json'))['map']
    overlap_keys = set(map_out) & set(verified)
    agree = sum(1 for k in overlap_keys if map_out[k] == verified[k])
    print(f"\noverlap with verified: {len(overlap_keys)}, agree: {agree}")
    if overlap_keys:
        print("Sample disagreements:")
        for k in list(overlap_keys)[:10]:
            if map_out[k] != verified[k]:
                print(f"  {k}: pathB={map_out[k]} verified={verified[k]}")
        if agree == len(overlap_keys):
            print("  (none — full agreement)")

    new_keys = set(map_out) - set(verified)
    print(f"\nNEW (page, idx) keys from path B: {len(new_keys)}")

    Path('.moneo-artifacts/glyph-map-pathB.json').write_text(json.dumps({
        "map": map_out, "confidence": conf,
        "votes": {f"F{k[0]},{k[1]}": dict(v) for k, v in votes.items()},
    }, ensure_ascii=False, indent=1))
    print("Wrote .moneo-artifacts/glyph-map-pathB.json")


if __name__ == "__main__":
    main()
