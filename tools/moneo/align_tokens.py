#!/usr/bin/env python3
"""Build a (page, idx) -> Hangul map by aligning token sequences against
ground-truth Korean text OCR'd from full framebuffers.

Strategy:
  1. For each frame X with a saved framebuffer, OCR with tesseract kor.
  2. Extract chronological token sequence for the period leading up to X
     (since the previous text-bearing frame).
  3. Align Hangul characters from OCR to Korean tokens 1:1 (skipping
     non-Korean bytes between tokens by tracking strptr deltas).
  4. Accumulate (page, idx) -> char votes; majority wins.
"""
import json, subprocess, tempfile, os, re
from pathlib import Path
from collections import defaultdict, Counter
from PIL import Image


def ocr_fb(fb_path):
    img = Image.frombytes('RGBA', (240, 160), Path(fb_path).read_bytes()).convert('L')
    # Upscale + invert if needed
    big = img.resize((240*4, 160*4), Image.LANCZOS)
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tf:
        big.save(tf.name)
        tmp = tf.name
    try:
        out = subprocess.run(['tesseract', tmp, '-', '-l', 'kor', '--psm', '6'],
                             capture_output=True, text=True, timeout=15)
        return out.stdout.strip()
    finally:
        os.unlink(tmp)


def hangul_only(s):
    return [c for c in s if '\uAC00' <= c <= '\uD7A3']


def main():
    cap = json.load(open('.moneo-artifacts/capture-fb.json'))
    tokens = cap['tokens']
    print(f"tokens: {len(tokens)}")
    # Index tokens by frame
    tokens_sorted = sorted(tokens, key=lambda t: t['frame'])

    fb_dir = Path('.moneo-artifacts/dumps/fb-seq')
    fbs = sorted(fb_dir.glob('fb-*.bin'))
    print(f"framebuffers: {len(fbs)}")

    # For each FB, OCR and get hangul characters in render order
    fb_data = []
    for fb in fbs:
        m = re.search(r'(\d+)\.bin$', fb.name)
        frame = int(m.group(1))
        text = ocr_fb(fb)
        h = hangul_only(text)
        fb_data.append((frame, text, h))
        print(f"  fb@{frame}: {len(h)} hangul: {''.join(h)[:60]}")

    # Now: for each FB at frame X, the tokens that drew its text fired between
    # the previous FB's frame and X. We assume the text on screen at X is the
    # MOST RECENT text drawn (cumulative is wrong if text scrolled).
    # Simpler: take tokens in window [X - W, X], where W is chosen to capture
    # a typical text-rendering burst.
    votes = defaultdict(Counter)

    W = 200  # tokens within last 200 frames

    for i, (frame, text, h) in enumerate(fb_data):
        if not h:
            continue
        # Tokens whose frame is in (frame - W, frame]
        lo = frame - W
        ts = [t for t in tokens_sorted if lo < t['frame'] <= frame]
        # Sort by frame then strptr (correct chronological order within burst)
        ts.sort(key=lambda t: (t['frame'], t['strptr']))
        # If token count and hangul count aren't equal, alignment is ambiguous
        # (text may include earlier text too). Take a heuristic: align the LAST
        # len(h) tokens to h.
        if len(ts) >= len(h):
            tail = ts[-len(h):]
            for t, ch in zip(tail, h):
                votes[(t['page'], t['idx'])][ch] += 1

    # Output: for each (page, idx) take majority char
    map_out = {}
    confidence = {}
    for key, c in votes.items():
        ch, n = c.most_common(1)[0]
        total = sum(c.values())
        map_out[f"F{key[0]},{key[1]}"] = ch
        confidence[f"F{key[0]},{key[1]}"] = n / total

    print(f"\nVoted {len(map_out)} (page, idx) keys from {len(fb_data)} framebuffers.")
    Path('.moneo-artifacts/glyph-map-aligned.json').write_text(
        json.dumps({"map": map_out, "confidence": confidence,
                    "votes": {f"F{k[0]},{k[1]}": dict(v) for k, v in votes.items()}},
                   ensure_ascii=False, indent=1))
    print("Wrote .moneo-artifacts/glyph-map-aligned.json")

    # Compare with OCR-per-glyph
    ocr_map = json.load(open('tools/moneo/glyph-map-ocr.json'))['map']
    agree = sum(1 for k, ch in map_out.items() if ocr_map.get(k) == ch)
    disagree = sum(1 for k, ch in map_out.items() if ocr_map.get(k) and ocr_map.get(k) != ch)
    print(f"agree with per-glyph OCR: {agree}, disagree: {disagree}")
    # Print top disagreements
    print("\nDisagreements (aligned -> per-glyph OCR), sorted by aligned-conf:")
    rows = sorted(map_out.items(), key=lambda kv: -confidence[kv[0]])
    shown = 0
    for k, ch in rows:
        if ocr_map.get(k) and ocr_map.get(k) != ch:
            print(f"  {k}: aligned={ch} (conf={confidence[k]:.2f}, votes={dict(votes[(int(k[1:].split(',')[0]), int(k.split(',')[1]))])}) ocr={ocr_map.get(k)}")
            shown += 1
            if shown >= 15: break


if __name__ == "__main__":
    main()
