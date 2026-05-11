#!/usr/bin/env python3
"""Reconciliation round 1: context-only labels for LIS-broken codepoints.

These cps violate the LIS bracket but their syllable is unambiguous from
corpus context. The patch authors appear to use a frequency-based
encoding that pulls common Korean verb roots / conjugational auxiliaries
out of Unicode collation order and into a contiguous mid-range block —
which breaks LIS-bracket inference for exactly those high-frequency cps.

Single-batch wins (~28% of remaining unknown occurrences in one shot):

  0x3A37 = 하  (339 occ — "do" auxiliary stem: 하고, 하면, 하지)
  0x3B38 = 있  (339 occ — "be/exist": 있어, 있다, 있지)
  0x3B39 = 만  (111 occ — "만들다" stem: 만들면, 만든)
  0x3920 = 됐  ( 58 occ — past-tense of 되다: 됐다고, 됐어)
  0x3F37 = 함  ( 24 occ — "함께" first syllable)

Applies them directly to codepoint_map.json with NO LIS-bracket check.
"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP = HERE / "codepoint_map.json"

OVERRIDES = {
    "3920": "됐",
    "3A37": "하",
    "3B38": "있",
    "3B39": "만",
    "3F37": "함",
}


def main():
    raw = json.load(open(MAP))
    before = len(raw)
    added = []
    for cp_hex, ch in OVERRIDES.items():
        cp_hex = cp_hex.upper()
        if cp_hex in raw:
            if raw[cp_hex] != ch:
                print(f"  CONFLICT {cp_hex}: have {raw[cp_hex]!r}, override {ch!r}")
                raw[cp_hex] = ch
        else:
            raw[cp_hex] = ch
            added.append((cp_hex, ch))
    out_sorted = {k: raw[k] for k in sorted(raw, key=lambda h: int(h, 16))}
    MAP.write_text(json.dumps(out_sorted, indent=2, ensure_ascii=False) + "\n")
    print(f"before {before}, after {len(out_sorted)} (+{len(added)} overrides)")


if __name__ == "__main__":
    main()
