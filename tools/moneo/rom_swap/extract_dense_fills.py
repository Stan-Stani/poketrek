#!/usr/bin/env python3
"""Extract just the deterministic dense-gap fills from the LIS analysis.

For every adjacent pair of LIS anchors where cp_gap == uni_gap (the
atlas slots between two anchors map 1:1 to the syllables in collation
order between them), emit those mappings. These are high-confidence
because no choice is involved -- the only assignment that preserves
both monotonicity and the slot count is the identity sequence.

Output: codepoint_map.dense.json (a delta to be merged into the main
codepoint_map.json).
"""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

KNOWN_MAP_PATH = Path(__file__).resolve().parent / "codepoint_map.json"
OUT = Path(__file__).resolve().parent / "codepoint_map.dense.json"


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
    raw = json.load(open(KNOWN_MAP_PATH))
    print(f"raw anchors: {len(raw)}")

    anchors = sorted([(int(k, 16), v, ord(v)) for k, v in raw.items()])
    lis = lis_by_unicode(anchors)
    print(f"LIS by unicode: {len(lis)}")

    fills = {}
    corrections = {}
    pairs_dense = 0
    for i in range(1, len(lis)):
        cp_a, syl_a, uni_a = lis[i - 1]
        cp_b, syl_b, uni_b = lis[i]
        cp_gap = cp_b - cp_a - 1
        uni_gap = uni_b - uni_a - 1
        if cp_gap == 0 or cp_gap != uni_gap:
            continue
        intermediate_cps = [c for c in range(cp_a + 1, cp_b)
                            if (c & 0xFF) != 0xFF]
        if len(intermediate_cps) != cp_gap:
            continue
        intermediate_chars = [chr(uni_a + 1 + k) for k in range(cp_gap)]
        for cp, ch in zip(intermediate_cps, intermediate_chars):
            cp_hex = f"{cp:04X}"
            if cp_hex in raw:
                # Conflict: raw says X, dense fill says Y. The cp is between
                # two monotonic LIS anchors, so the dense fill answer is the
                # only valid syllable. The raw entry is a triangulation
                # error to be replaced.
                if raw[cp_hex] != ch:
                    corrections[cp_hex] = {
                        "raw": raw[cp_hex],
                        "corrected_to": ch,
                        "anchor_a": f"0x{cp_a:04X}={syl_a}",
                        "anchor_b": f"0x{cp_b:04X}={syl_b}",
                        "method": "dense_gap_correction",
                    }
                continue
            fills[cp_hex] = {
                "match": ch,
                "anchor_a": f"0x{cp_a:04X}={syl_a}",
                "anchor_b": f"0x{cp_b:04X}={syl_b}",
                "method": "dense_gap_fill",
            }
        pairs_dense += 1

    OUT.write_text(json.dumps({
        "version": 1,
        "method": "dense gap fill: between LIS anchors where cp_gap == "
                  "unicode_gap, intermediate cps map 1:1 to syllables in "
                  "collation order. Deterministic (no OCR).",
        "stats": {
            "lis_size": len(lis),
            "dense_pairs": pairs_dense,
            "new_mappings": len(fills),
            "corrections": len(corrections),
        },
        "mappings": {cp: f["match"] for cp, f in fills.items()},
        "corrections": {cp: c["corrected_to"] for cp, c in corrections.items()},
        "details": {"fills": fills, "corrections": corrections},
    }, indent=2, ensure_ascii=False))
    print(f"\nemitted {len(fills)} new mappings + {len(corrections)} "
          f"corrections to {OUT}")
    print("sample fills:")
    for cp, f in list(fills.items())[:10]:
        print(f"  {cp} -> {f['match']!r}  (between {f['anchor_a']} "
              f"and {f['anchor_b']})")
    print("sample corrections (raw -> corrected):")
    for cp, c in list(corrections.items())[:10]:
        print(f"  {cp}  {c['raw']!r} -> {c['corrected_to']!r}  "
              f"(between {c['anchor_a']} and {c['anchor_b']})")


if __name__ == "__main__":
    main()
