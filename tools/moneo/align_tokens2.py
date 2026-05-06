#!/usr/bin/env python3
"""Better aligner: group tokens into bursts (strptr deltas + frame gaps),
OCR the framebuffer at burst end, align Korean tokens to Hangul chars,
and accumulate votes (page, idx) -> char.

Concurrency: parallel OCR of unique FBs (one FB per burst).
"""
import json, subprocess, tempfile, os, re, sys
from pathlib import Path
from collections import defaultdict, Counter
from PIL import Image
from concurrent.futures import ProcessPoolExecutor, as_completed


CAPTURE = '.moneo-artifacts/capture-long-aligned.json'
FB_DIR = Path('.moneo-artifacts/dumps/fb-seq-long')


def ocr_one(fb_path):
    img = Image.frombytes('RGBA', (240, 160), Path(fb_path).read_bytes()).convert('L')
    big = img.resize((240*4, 160*4), Image.LANCZOS)
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tf:
        big.save(tf.name)
        tmp = tf.name
    try:
        out = subprocess.run(['tesseract', tmp, '-', '-l', 'kor', '--psm', '6'],
                             capture_output=True, text=True, timeout=20)
        return Path(fb_path).name, out.stdout
    finally:
        os.unlink(tmp)


def hangul_only(s):
    return [c for c in s if '\uAC00' <= c <= '\uD7A3']


def parse_fb_frame(name):
    m = re.search(r'(\d+)\.bin$', name)
    return int(m.group(1)) if m else None


def main():
    cap = json.load(open(CAPTURE))
    tokens = sorted(cap['tokens'], key=lambda t: (t['frame'], t['strptr']))
    print(f"tokens: {len(tokens)}")

    # Group into bursts: a new burst when frame gap > 60 OR strptr decreases
    # (strptr decrease = new buffer = new textbox)
    bursts = []
    cur = []
    last_frame = -1
    last_strptr = -1
    for t in tokens:
        new_burst = (last_frame >= 0 and (t['frame'] - last_frame > 90 or t['strptr'] < last_strptr - 200))
        if new_burst and cur:
            bursts.append(cur); cur = []
        cur.append(t)
        last_frame = t['frame']; last_strptr = t['strptr']
    if cur: bursts.append(cur)

    print(f"bursts: {len(bursts)}")

    # For each burst, pick the closest FB at-or-after the burst's last frame
    fbs = sorted(FB_DIR.glob('fb-*.bin'))
    fb_frames = [parse_fb_frame(f.name) for f in fbs]

    burst_fb = []
    for b in bursts:
        last_t = b[-1]['frame']
        # Closest FB within +120 frames of last token (text settled)
        candidates = [(f, fp) for f, fp in zip(fb_frames, fbs) if last_t <= f <= last_t + 120]
        if candidates:
            f, fp = candidates[0]
            burst_fb.append((b, fp, f))

    print(f"bursts with matching FB: {len(burst_fb)}")

    # OCR unique FBs in parallel
    unique_fbs = list({str(fp) for _, fp, _ in burst_fb})
    print(f"unique FBs to OCR: {len(unique_fbs)}")
    ocr_results = {}
    with ProcessPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(ocr_one, fp): fp for fp in unique_fbs}
        done = 0
        for fut in as_completed(futs):
            name, text = fut.result()
            ocr_results[name] = text
            done += 1
            if done % 20 == 0: print(f"  ocr {done}/{len(unique_fbs)}")

    # Print samples
    print("\n--- sample FB OCR ---")
    for fp in unique_fbs[:6]:
        h = ''.join(hangul_only(ocr_results.get(Path(fp).name, '')))
        print(f"  {Path(fp).name}: {h[:60]}")

    # Align: for each burst, take its tokens and the OCR'd hangul of the FB.
    # Align last len(tokens) hangul chars to tokens (the new text shown in this
    # burst — earlier visible text may have been from previous bursts).
    votes = defaultdict(Counter)
    aligned_bursts = 0
    for b, fp, _ in burst_fb:
        text = ocr_results.get(Path(fp).name, '')
        h = hangul_only(text)
        if not h: continue
        if len(h) >= len(b):
            tail = h[-len(b):]
            for t, ch in zip(b, tail):
                votes[(t['page'], t['idx'])][ch] += 1
            aligned_bursts += 1
        else:
            # tokens > visible chars: align first len(h) tokens
            head = b[:len(h)]
            for t, ch in zip(head, h):
                votes[(t['page'], t['idx'])][ch] += 1
            aligned_bursts += 1

    print(f"\naligned bursts: {aligned_bursts}")
    print(f"unique (page, idx) keys: {len(votes)}")

    # Build map from votes (majority, but only if >= 2 votes OR 1 vote with single token)
    map_out = {}
    confidence = {}
    for key, c in votes.items():
        ch, n = c.most_common(1)[0]
        total = sum(c.values())
        # Require either 2+ votes or only-one-vote-but-clean
        if n >= 2 or (total == 1 and n == 1):
            map_out[f"F{key[0]},{key[1]}"] = ch
            confidence[f"F{key[0]},{key[1]}"] = n / total

    print(f"\nfinal map size: {len(map_out)}")

    # Compare to per-glyph OCR
    ocr_map = json.load(open('tools/moneo/glyph-map-ocr.json'))['map']
    agree = sum(1 for k, ch in map_out.items() if ocr_map.get(k) == ch)
    print(f"agree with per-glyph OCR: {agree}/{len(map_out)}")

    Path('.moneo-artifacts/glyph-map-aligned.json').write_text(
        json.dumps({"map": map_out, "confidence": confidence,
                    "votes": {f"F{k[0]},{k[1]}": dict(v) for k, v in votes.items()}},
                   ensure_ascii=False, indent=1))
    print("Wrote .moneo-artifacts/glyph-map-aligned.json")


if __name__ == "__main__":
    main()
