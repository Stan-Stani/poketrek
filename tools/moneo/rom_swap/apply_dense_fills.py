#!/usr/bin/env python3
"""Build the cleaned codepoint_map by combining:
  1. The longest-increasing-subsequence subset of the raw 539 anchors
     (drops 20 that break Unicode monotonicity = likely triangulation
     errors).
  2. The dense-gap fills produced by extract_dense_fills.py
     (deterministic syllable assignments between LIS anchors where
     cp_gap == unicode_gap).
  3. The dense-gap corrections (where the raw map disagrees with what
     monotonicity demands; the LIS-implied answer wins).

Writes the merged map to codepoint_map.json (overwriting it). The
previous file is backed up to codepoint_map.raw.json.
"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "codepoint_map.json"
BACKUP = HERE / "codepoint_map.raw.json"
DENSE = HERE / "codepoint_map.dense.json"


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
    raw = json.load(open(RAW))
    print(f"raw anchors: {len(raw)}")
    if not BACKUP.exists():
        BACKUP.write_text(json.dumps(raw, indent=2, ensure_ascii=False))
        print(f"backed up raw to {BACKUP}")

    dense_data = json.load(open(DENSE))
    fills = dense_data["mappings"]
    corrections = dense_data["corrections"]
    print(f"dense fills: {len(fills)}")
    print(f"dense corrections: {len(corrections)}")

    # Compute LIS keep-set
    anchors = sorted([(int(k, 16), v, ord(v)) for k, v in raw.items()])
    lis = lis_by_unicode(anchors)
    lis_cps = {f"{cp:04X}": syl for cp, syl, _ in lis}
    dropped = [cp_hex for cp_hex in raw if cp_hex not in lis_cps]
    print(f"LIS-kept anchors: {len(lis_cps)}")
    print(f"dropped non-monotonic anchors: {len(dropped)}")

    # Merge: LIS + corrections override + dense fills
    merged = dict(lis_cps)
    for cp_hex, ch in corrections.items():
        merged[cp_hex] = ch
    for cp_hex, ch in fills.items():
        merged[cp_hex] = ch
    print(f"merged total: {len(merged)}")

    # Sort by cp for stable diffs
    out_sorted = {k: merged[k] for k in sorted(merged, key=lambda h: int(h, 16))}
    RAW.write_text(json.dumps(out_sorted, indent=2, ensure_ascii=False))
    print(f"wrote merged map to {RAW}")


if __name__ == "__main__":
    main()
