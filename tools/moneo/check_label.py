#!/usr/bin/env python3
"""Inspect the contexts in which each (page,idx)->char mapping is used.

Helps detect mislabels: if 'F4,157=마' actually appears between context
suggesting '수' or '약', the label is wrong.

Usage:
  python3 tools/moneo/check_label.py 마           # all keys mapped to 마
  python3 tools/moneo/check_label.py F4,157       # just one key
"""
from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
GMAP = json.loads((ROOT / "tools/moneo/glyph-map.json").read_text(encoding="utf-8"))["map"]
RAW = json.loads((ROOT / ".moneo-artifacts/rom-text-ko-raw.json").read_text(encoding="utf-8"))["records"]


def decode_with_marker(bs, target_page, target_idx):
    out, positions = [], []
    i, n = 0, len(bs)
    while i < n:
        b = bs[i]
        if b == 0xFF: break
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
                ch = GMAP.get(f"F{page},{idx}")
                out.append(ch if ch else "□")
            i += 2; continue
        if b in (0xF7, 0xF8, 0xF9) and i + 1 < n:
            out.append("?"); i += 2; continue
        if b == 0:
            i += 1; continue
        ch = GMAP.get(f"F0,{b}")
        if ch is not None: out.append(ch)
        elif 0x20 <= b <= 0x7E: out.append(chr(b))
        else: out.append("·")
        i += 1
    return "".join(out), positions


def gather(page, idx, max_samples=15, width=12):
    samples = []
    for rec in RAW:
        hex_str = rec.get("hex", "")
        if not hex_str: continue
        bs = [int(hex_str[j:j+2], 16) for j in range(0, len(hex_str), 2)]
        # quick filter
        ok = False
        for k in range(len(bs) - 1):
            if bs[k] == 0xF0 + page and bs[k+1] == idx:
                ok = True; break
        if not ok: continue
        decoded, positions = decode_with_marker(bs, page, idx)
        for pos in positions:
            lo = max(0, pos - width)
            hi = min(len(decoded), pos + width + 1)
            samples.append(decoded[lo:hi].replace("\n", "/"))
            if len(samples) >= max_samples: break
        if len(samples) >= max_samples: break
    return samples


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="Hangul char or F<p>,<i>")
    ap.add_argument("--width", type=int, default=10)
    ap.add_argument("--samples", type=int, default=12)
    args = ap.parse_args()

    if "," in args.query:
        keys = [args.query.lstrip("F")]
    else:
        # find all keys mapped to this char
        keys = [k.lstrip("F") for k, v in GMAP.items() if v == args.query]

    for k in keys:
        p_str, i_str = k.split(",")
        p, i = int(p_str), int(i_str)
        ch = GMAP.get(f"F{p},{i}", "?")
        samples = gather(p, i, args.samples, args.width)
        print(f"\n=== F{p},{i}  =  {ch}  ({len(samples)} samples) ===")
        for s in samples:
            print(f"  {s}")


if __name__ == "__main__":
    main()
