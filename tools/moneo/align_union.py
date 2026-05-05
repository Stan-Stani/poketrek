#!/usr/bin/env python3
"""Union alignment results across multiple captures + their FB dirs.
Combines votes; majority wins; only keeps high-confidence entries.
"""
import json, subprocess, tempfile, os, re, sys
from pathlib import Path
from collections import defaultdict, Counter
from PIL import Image
from concurrent.futures import ProcessPoolExecutor, as_completed

CAPTURES = [
    ('.moneo-artifacts/capture-fb.json',           '.moneo-artifacts/dumps/fb-seq'),
    ('.moneo-artifacts/capture-walk.json',         '.moneo-artifacts/dumps/fb-walk'),
    ('.moneo-artifacts/capture-fresh.json',        '.moneo-artifacts/dumps/fb-fresh'),
    ('.moneo-artifacts/capture-long-aligned.json', '.moneo-artifacts/dumps/fb-seq-long'),
]


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


def process_capture(cap_path, fb_dir):
    cap = json.load(open(cap_path))
    tokens = sorted(cap['tokens'], key=lambda t: (t['frame'], t['strptr']))
    # Strict string grouping
    strings = []; cur = []
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

    fbs = sorted(Path(fb_dir).glob('fb-*.bin'))
    fb_frames = [(parse_fb_frame(f.name), f) for f in fbs]

    string_fb = []
    for s in strings:
        end = s[-1]['frame']
        cands = [(f, fp) for f, fp in fb_frames if end <= f <= end + 200]
        if cands: string_fb.append((s, cands[0][1]))

    return string_fb


def main():
    all_pairs = []
    for cap, fbd in CAPTURES:
        if not Path(cap).exists() or not Path(fbd).exists():
            print(f"skip {cap}")
            continue
        pairs = process_capture(cap, fbd)
        print(f"{cap}: {len(pairs)} pairs")
        all_pairs.extend(pairs)

    # OCR all unique FBs in parallel
    unique_fbs = sorted({str(fp) for _, fp in all_pairs})
    print(f"\nunique FBs: {len(unique_fbs)}")
    ocr = {}
    with ProcessPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(ocr_one, fp): fp for fp in unique_fbs}
        for i, fut in enumerate(as_completed(futs)):
            n, t = fut.result(); ocr[n] = t
            if (i+1) % 100 == 0: print(f"  ocr {i+1}/{len(unique_fbs)}")

    # Vote
    votes = defaultdict(Counter)
    aligned = 0
    for s, fp in all_pairs:
        text = ocr.get(Path(fp).name, '')
        h = hangul_only(text)
        if not h: continue
        if len(h) >= len(s):
            tail = h[-len(s):]
            for t, ch in zip(s, tail):
                votes[(t['page'], t['idx'])][ch] += 1
        else:
            for t, ch in zip(s[:len(h)], h):
                votes[(t['page'], t['idx'])][ch] += 1
        aligned += 1
    print(f"aligned: {aligned}, unique keys: {len(votes)}")

    # Build map
    map_out = {}; conf = {}
    for k, c in votes.items():
        ch, n = c.most_common(1)[0]
        total = sum(c.values())
        if n >= 2 and n / total >= 0.5:
            map_out[f"F{k[0]},{k[1]}"] = ch
            conf[f"F{k[0]},{k[1]}"] = n / total

    print(f"high-conf entries (>=2 votes & >=50%): {len(map_out)}")
    pages = Counter(int(k[1:].split(',')[0]) for k in map_out)
    print(f"per page: {dict(pages)}")

    Path('.moneo-artifacts/glyph-map-union.json').write_text(json.dumps({
        "map": map_out, "confidence": conf,
        "votes": {f"F{k[0]},{k[1]}": dict(v) for k, v in votes.items()},
    }, ensure_ascii=False, indent=1))
    print("Wrote .moneo-artifacts/glyph-map-union.json")


if __name__ == "__main__":
    main()
