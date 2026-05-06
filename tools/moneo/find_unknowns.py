#!/usr/bin/env python3
"""Find top-frequency unlabeled (page,idx) tokens with surrounding context.

Helps the contextual labeling workflow: shows samples around each unknown
glyph so you can guess the syllable from neighboring (already-labeled) text.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
GLYPH_MAP_PATH = ROOT / "tools/moneo/glyph-map.json"
RAW_PATH = ROOT / ".moneo-artifacts/rom-text-ko-raw.json"


def decode_context(bs, glyph_map, target_page, target_idx):
    out, positions = [], []
    i, n = 0, len(bs)
    while i < n:
        b = bs[i]
        if b == 0xFF:
            break
        if b == 0xFE:
            out.append("/"); i += 1; continue
        if b in (0xFA, 0xFB):
            out.append("|"); i += 1; continue
        if b in (0xFC, 0xFD) and i + 1 < n:
            out.append("$"); i += 2; continue
        if 0xF1 <= b <= 0xF6 and i + 1 < n:
            page = b - 0xF0
            idx = bs[i + 1]
            if page == target_page and idx == target_idx:
                positions.append(len(out))
                out.append("◆")
            else:
                ch = glyph_map.get(f"F{page},{idx}")
                out.append(ch if ch else "□")
            i += 2; continue
        if b in (0xF7, 0xF8, 0xF9) and i + 1 < n:
            out.append("?"); i += 2; continue
        if b == 0:
            i += 1; continue
        ch = glyph_map.get(f"F0,{b}")
        if ch is not None:
            out.append(ch)
        elif 0x20 <= b <= 0x7E:
            out.append(chr(b))
        else:
            out.append("·")
        i += 1
    return "".join(out), positions


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=50)
    ap.add_argument("--samples", type=int, default=8)
    ap.add_argument("--width", type=int, default=10, help="context chars each side")
    ap.add_argument("--only", help="Only this F<p>,<i> key (or comma-separated)")
    args = ap.parse_args()

    glyph_map = json.loads(GLYPH_MAP_PATH.read_text(encoding="utf-8"))["map"]
    raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))["records"]

    only_set = None
    if args.only:
        only_set = set(args.only.split(","))

    # Pre-decode all records as byte arrays once
    all_recs = []
    for rec in raw:
        hex_str = rec.get("hex", "")
        if not hex_str:
            continue
        bs = [int(hex_str[j:j+2], 16) for j in range(0, len(hex_str), 2)]
        all_recs.append((rec.get("offset"), bs))

    counts = Counter()
    for _, bs in all_recs:
        i, n = 0, len(bs)
        while i < n:
            b = bs[i]
            if b == 0xFF:
                break
            if b == 0xFE or b in (0xFA, 0xFB):
                i += 1; continue
            if b in (0xFC, 0xFD) and i + 1 < n:
                i += 2; continue
            if 0xF1 <= b <= 0xF6 and i + 1 < n:
                page = b - 0xF0
                idx = bs[i + 1]
                key = f"F{page},{idx}"
                if key not in glyph_map:
                    counts[(page, idx)] += 1
                i += 2; continue
            if b in (0xF7, 0xF8, 0xF9) and i + 1 < n:
                i += 2; continue
            i += 1

    targets = counts.most_common(args.top)
    if only_set:
        targets = [((p, i), c) for (p, i), c in counts.most_common()
                   if f"F{p},{i}" in only_set]

    print(f"# Unlabeled glyph hotlist (top {len(targets)}):\n")
    for (p, idx), c in targets:
        samples = []
        for off, bs in all_recs:
            has = any(bs[k] == 0xF0 + p and bs[k + 1] == idx
                      for k in range(len(bs) - 1))
            if not has:
                continue
            decoded, positions = decode_context(bs, glyph_map, p, idx)
            for pos in positions:
                lo = max(0, pos - args.width)
                hi = min(len(decoded), pos + args.width + 1)
                snippet = decoded[lo:hi].replace("\n", "/")
                samples.append(snippet)
                if len(samples) >= args.samples:
                    break
            if len(samples) >= args.samples:
                break
        sep = "   |   "
        print(f"F{p},{idx:<3d}  ×{c:<4d}  {sep.join(samples)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
