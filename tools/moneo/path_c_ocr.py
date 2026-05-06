#!/usr/bin/env python3
"""Path C v2: render every (page, idx) glyph from the blit-table-derived
4bpp pixel data and OCR.

This time we use the VERIFIED blit pipeline (table1 + table2) so the rendered
pixels match what the runtime actually draws (modulo shadow fill, which we
add to mimic in-game appearance).

Validate against tools/moneo/glyph-map.json (88 verified entries) before
trusting any output.
"""
from __future__ import annotations
import hashlib, json, struct, subprocess, tempfile, os, re, sys
from pathlib import Path
from collections import Counter
from PIL import Image
from concurrent.futures import ProcessPoolExecutor, as_completed

ROM = bytes(Path("Pocket Monsters - LeafGreen (Korean).gba").read_bytes())
IWRAM = bytes(Path(".moneo-artifacts/dumps/iwram.bin").read_bytes())
# Korean font pages F1..F6 — file offsets read from the pointer table at
# ROM 0x0838492C (entries 1..6; entry 0 is the non-Korean base font).
KOREAN_FONT_BASES = [0x780000, 0x784000, 0x788000, 0x78C000, 0x790000, 0x794000]
table1 = ROM[0x1CDF1C : 0x1CDF1C + 256]
table2 = struct.unpack_from("<256H", IWRAM, 0x0A40)


def glyph_base_offsets(p, i):
    """Return (TL_off, TR_off, BL_off, BR_off) ROM file offsets for the four
    8x8 sub-tiles of glyph (p, i). 8 glyphs per stripe, glyph is 16x16."""
    page_base = KOREAN_FONT_BASES[p - 1]
    stripe = i // 8
    col = i % 8
    base = page_base + stripe * 512 + col * 32
    return base, base + 16, base + 256, base + 272


def blit_tile_v(rom_off):
    out = bytearray(32)
    for hw in range(8):
        b0 = ROM[rom_off + hw*2]; b1 = ROM[rom_off + hw*2 + 1]
        v0 = table2[table1[b0]]; v1 = table2[table1[b1]]
        out[hw*4+0] = v0 & 0xFF; out[hw*4+1] = (v0>>8)&0xFF
        out[hw*4+2] = v1 & 0xFF; out[hw*4+3] = (v1>>8)&0xFF
    return bytes(out)


# Render a 16x16 glyph from 4 sub-tiles.
def render_glyph(p, i):
    """Return PIL.Image (16x16, mode L) where glyph pixels are dark on white."""
    tl, tr, bl, br = glyph_base_offsets(p, i)
    sub_offs = [(0, 0, tl), (8, 0, tr), (0, 8, bl), (8, 8, br)]
    img = Image.new('L', (16, 16), 255)
    px = img.load()
    for sx, sy, sub_off in sub_offs:
        tile = blit_tile_v(sub_off)
        for row in range(8):
            for col_pair in range(4):
                b = tile[row*4 + col_pair]
                lo = b & 0x0F; hi = (b >> 4) & 0x0F
                def shade(v):
                    return 255 if v in (0, 1) else (0 if v == 2 else 64)
                px[sx + col_pair*2,     sy + row] = shade(lo)
                px[sx + col_pair*2 + 1, sy + row] = shade(hi)
    return img


def is_blank(p, i):
    for off in glyph_base_offsets(p, i):
        if any(b for b in blit_tile_v(off)):
            return False
    return True


def ocr_glyph(args):
    p, i = args
    if is_blank(p, i): return (p, i, None, [])
    img = render_glyph(p, i)
    # Upscale 16x with white border
    big = img.resize((256, 256), Image.NEAREST)
    pad = Image.new('L', (320, 320), 255)
    pad.paste(big, (32, 32))
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tf:
        pad.save(tf.name); tmp = tf.name
    try:
        votes = Counter()
        for psm in (10, 8, 7, 6):
            r = subprocess.run(['tesseract', tmp, '-', '-l', 'kor', '--psm', str(psm)],
                               capture_output=True, text=True, timeout=10)
            for c in r.stdout:
                if '\uAC00' <= c <= '\uD7A3':
                    votes[c] += 1
                    break
        if not votes: return (p, i, None, [])
        best, _ = votes.most_common(1)[0]
        return (p, i, best, votes.most_common())
    finally:
        os.unlink(tmp)


def main():
    cands = [(p, i) for p in range(1, 7) for i in range(256)]
    print(f"glyphs to OCR: {len(cands)}")
    out_map = {}; out_votes = {}
    with ProcessPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(ocr_glyph, pi): pi for pi in cands}
        for j, fut in enumerate(as_completed(futs)):
            p, i, ch, votes = fut.result()
            if ch:
                out_map[f"F{p},{i}"] = ch
                out_votes[f"F{p},{i}"] = votes
            if (j+1) % 100 == 0:
                print(f"  ocr {j+1}/{len(cands)}, mapped {len(out_map)}")
    print(f"\nMapped {len(out_map)} non-blank glyphs.")

    # Validate
    verified = json.load(open('tools/moneo/glyph-map.json'))['map']
    common = set(out_map) & set(verified)
    agree = sum(1 for k in common if out_map[k] == verified[k])
    print(f"validation: {agree}/{len(common)} agree with verified set ({len(verified)} entries)")
    print("\nDisagreements:")
    for k in sorted(common):
        if out_map[k] != verified[k]:
            print(f"  {k}: pathC2={out_map[k]} verified={verified[k]} votes={out_votes[k]}")

    Path('.moneo-artifacts/glyph-map-pathC2.json').write_text(
        json.dumps({"map": out_map, "votes": out_votes}, ensure_ascii=False, indent=1))
    print("\nWrote .moneo-artifacts/glyph-map-pathC2.json")


if __name__ == "__main__":
    main()
