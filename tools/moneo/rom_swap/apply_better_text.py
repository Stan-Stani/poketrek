#!/usr/bin/env python3
"""Apply two more batches of high-confidence labels to codepoint_map.json:

1. Deterministic-bracket unknowns: any unknown cp whose LIS bracket
   yields exactly one candidate is FORCED -- the only valid syllable
   in that window.
2. LIS-validated triangulation predictions: from
   codepoint_suggestions_filtered.json (validated list).
"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP = HERE / "codepoint_map.json"
SUGG = HERE.parent / "codepoint_suggestions_filtered.json"
UNKNOWNS = HERE.parent / "codepoint_unknowns_2024.json"

HANGUL_LO = 0xAC00
HANGUL_HI = 0xD7A3


def lis_by_unicode(anchors):
    n = len(anchors)
    if n == 0: return []
    dp = [1] * n
    prev = [-1] * n
    for i in range(n):
        for j in range(i):
            if anchors[j][2] < anchors[i][2] and dp[j] + 1 > dp[i]:
                dp[i] = dp[j] + 1
                prev[i] = j
    end = max(range(n), key=lambda i: dp[i])
    seq = []
    while end != -1:
        seq.append(anchors[end])
        end = prev[end]
    return list(reversed(seq))


def main():
    raw = json.load(open(MAP))
    print(f"current map size: {len(raw)}")

    anchors = sorted([(int(k, 16), v, ord(v)) for k, v in raw.items()])
    lis = lis_by_unicode(anchors)
    print(f"LIS: {len(lis)}")

    def find_brackets(cp):
        prev_a, next_a = None, None
        for a in lis:
            if a[0] < cp:
                prev_a = a
            elif a[0] > cp and next_a is None:
                next_a = a; break
        lo = (prev_a[2] + 1) if prev_a else HANGUL_LO
        hi = (next_a[2] - 1) if next_a else HANGUL_HI
        return prev_a, next_a, lo, hi

    # --- 1. Deterministic 1-candidate brackets ---
    deterministic = {}
    unknowns = json.load(open(UNKNOWNS))["unknowns"]
    for u in unknowns:
        cp = int(u["codepoint"][2:], 16)
        cp_hex = f"{cp:04X}"
        if cp_hex in raw:
            continue
        prev_a, next_a, lo, hi = find_brackets(cp)
        if prev_a is None or next_a is None:
            continue
        # Number of cps in atlas slot range
        cp_gap = next_a[0] - prev_a[0] - 1
        uni_gap = hi - lo + 1
        if uni_gap == 0:
            continue
        if uni_gap == 1 and cp_gap >= 1:
            # Only 1 candidate; cp_gap atlas slots all map to the same
            # candidate -- deterministic only if cp_gap == 1.
            if cp_gap == 1:
                deterministic[cp_hex] = chr(lo)

    # --- 2. LIS-validated triangulations ---
    triangulated = {}
    if SUGG.exists():
        sd = json.load(open(SUGG))
        for v in sd.get("validated", []):
            cp_hex = v["codepoint"][2:]
            triangulated[cp_hex] = v["predicted"]

    print(f"deterministic 1-candidate auto-fills: {len(deterministic)}")
    print(f"LIS-validated triangulations:        {len(triangulated)}")

    new_map = dict(raw)
    added = 0
    for cp_hex, ch in deterministic.items():
        if cp_hex not in new_map:
            new_map[cp_hex] = ch
            added += 1
    for cp_hex, ch in triangulated.items():
        if cp_hex not in new_map:
            new_map[cp_hex] = ch
            added += 1

    out_sorted = {k: new_map[k] for k in sorted(new_map, key=lambda h: int(h, 16))}
    MAP.write_text(json.dumps(out_sorted, indent=2, ensure_ascii=False))
    print(f"\nwrote map with {len(new_map)} entries (added {added})")
    print("sample new entries:")
    for cp_hex, ch in list(deterministic.items())[:8]:
        print(f"  det 1-cand:  {cp_hex} -> {ch!r}")
    for cp_hex, ch in triangulated.items():
        print(f"  triang:      {cp_hex} -> {ch!r}")


if __name__ == "__main__":
    main()
