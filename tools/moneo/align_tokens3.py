#!/usr/bin/env python3
"""Improved aligner v3.

Key insights:
- Within one rendered string, strptr is monotonically increasing. Tokens with
  decreasing strptr or with a long frame gap are a NEW string.
- Each FB shows the string after it finishes drawing. The frame the FB is
  taken should be > last token frame of the string but not too far past.
- Drop low-confidence votes.
"""
import json, subprocess, tempfile, os, re, sys
from pathlib import Path
from collections import defaultdict, Counter
from PIL import Image
from concurrent.futures import ProcessPoolExecutor, as_completed

CAPTURE = sys.argv[1] if len(sys.argv) > 1 else '.moneo-artifacts/capture-walk.json'
FB_DIR = Path(sys.argv[2] if len(sys.argv) > 2 else '.moneo-artifacts/dumps/fb-walk')
OUT = sys.argv[3] if len(sys.argv) > 3 else '.moneo-artifacts/glyph-map-aligned-v3.json'


def ocr_one(fb_path):
    img = Image.frombytes('RGBA', (240, 160), Path(fb_path).read_bytes()).convert('L')
    big = img.resize((240*4, 160*4), Image.LANCZOS)
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tf:
        big.save(tf.name); tmp = tf.name
    try:
        out = subprocess.run(['tesseract', tmp, '-', '-l', 'kor', '--psm', '6'],
                             capture_output=True, text=True, timeout=20)
        return Path(fb_path).name, out.stdout
    finally:
        os.unlink(tmp)


def hangul_only(s):
    return [c for c in s if '\uAC00' <= c <= '\uD7A3']


def parse_fb_frame(name):
    m = re.search(r'(\d+)\.bin$', name); return int(m.group(1)) if m else None


def main():
    cap = json.load(open(CAPTURE))
    tokens = sorted(cap['tokens'], key=lambda t: (t['frame'], t['strptr']))
    print(f"tokens: {len(tokens)}")

    # Strict string grouping: same strptr_base (within 256 bytes) AND
    # monotone strptr AND frame gap < 60.
    strings = []
    cur = []
    last_frame = -1; last_strptr = -1
    for t in tokens:
        if cur:
            same = (t['strptr'] >= last_strptr and t['strptr'] - last_strptr < 16
                    and t['frame'] - last_frame <= 60)
            if not same:
                strings.append(cur); cur = []
        cur.append(t)
        last_frame = t['frame']; last_strptr = t['strptr']
    if cur: strings.append(cur)
    print(f"strings: {len(strings)}")

    # Match each string to the FB taken right after its last token (same scene)
    fbs = sorted(FB_DIR.glob('fb-*.bin'))
    fb_frames = [(parse_fb_frame(f.name), f) for f in fbs]
    fb_frames.sort()

    string_fb = []
    for s in strings:
        end_frame = s[-1]['frame']
        # Pick FB at-or-after end, within 200 frames
        candidates = [(f, fp) for f, fp in fb_frames if end_frame <= f <= end_frame + 200]
        if candidates:
            string_fb.append((s, candidates[0][1]))
    print(f"strings paired to FB: {len(string_fb)}")

    # OCR unique FBs
    unique_fbs = sorted({str(fp) for _, fp in string_fb})
    print(f"unique FBs: {len(unique_fbs)}")
    ocr_results = {}
    with ProcessPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(ocr_one, fp): fp for fp in unique_fbs}
        done = 0
        for fut in as_completed(futs):
            name, text = fut.result()
            ocr_results[name] = text
            done += 1
            if done % 50 == 0: print(f"  ocr {done}/{len(unique_fbs)}")

    # Align
    votes = defaultdict(Counter)
    aligned_count = 0
    for s, fp in string_fb:
        text = ocr_results.get(Path(fp).name, '')
        h = hangul_only(text)
        if not h: continue
        # Take last len(s) hangul chars (the most recent string drawn)
        if len(h) >= len(s):
            tail = h[-len(s):]
            for t, ch in zip(s, tail):
                votes[(t['page'], t['idx'])][ch] += 1
            aligned_count += 1
        else:
            for t, ch in zip(s[:len(h)], h):
                votes[(t['page'], t['idx'])][ch] += 1
            aligned_count += 1

    print(f"aligned strings: {aligned_count}")
    print(f"unique (page, idx): {len(votes)}")

    # Build map with confidence threshold
    map_out = {}; conf = {}
    for k, c in votes.items():
        ch, n = c.most_common(1)[0]
        total = sum(c.values())
        # Accept if majority >= 2 votes OR single vote with no conflicts
        if n >= 2 or total == 1:
            map_out[f"F{k[0]},{k[1]}"] = ch
            conf[f"F{k[0]},{k[1]}"] = n / total

    print(f"map size (conf-filtered): {len(map_out)}")
    # Stats by page
    pages = Counter(int(k.split(',')[0][1:]) for k in map_out)
    print(f"per page: {dict(pages)}")

    Path(OUT).write_text(json.dumps({
        "map": map_out, "confidence": conf,
        "votes": {f"F{k[0]},{k[1]}": dict(v) for k, v in votes.items()},
    }, ensure_ascii=False, indent=1))
    print(f"Wrote {OUT}")

    # Spot-check: reconstruct first 6 strings using map
    print("\n--- reconstructed strings ---")
    for s in strings[:8]:
        seq = []
        for t in s:
            seq.append(map_out.get(f"F{t['page']},{t['idx']}", f"[{t['page']},{t['idx']}]"))
        print(f"  ({len(s)} toks): {''.join(c if len(c)==1 else '·' for c in seq)}")


if __name__ == "__main__":
    main()
