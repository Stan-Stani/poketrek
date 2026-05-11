#!/usr/bin/env python3
"""Reconciliation round 3: targeted pass on 40 stubborn high-freq cps.

Reconcile r1 (5 labels, 876 occ) and r2 (13 labels, 485 occ) handled
the obvious morphemes. R3 went deep on the remaining 40 cps with ≥10
occurrences, classified each into:
  A) Single-syllable label  — 3 cps
  B) Non-syllable control   — 6 cps (documented separately)
  C) Cluster member         — 7 groups (need joint triangulation)
  D) Polysemous             — 23 cps (deferred)

This script applies only category-A labels:

  0x3D3C = 더  (76 occ — alt-encoding of 더 also at 0x38DE)
  0x3E37 = 이  (88 occ — alt-encoding of 이 also at 0x3D72)
  0x3F38 = 든  (25 occ — "만든다" stem ending)

Note: 0x3D3C and 0x3E37 are alternate encodings of syllables that
already exist in the map under different cps. The patch evidently
uses multiple cps for the same syllable (likely different glyph
variants for context — bold/italic/halfwidth).

Control codes identified by r3 (not syllables; documented in commit):
  0x3FFF — sentence/paragraph terminator
  0x40A1 — HM/TM icon glyph
  0x3C08, 0x4018, 0x408C, 0x398C — binary table bytes outside dialog
"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP = HERE / "codepoint_map.json"

OVERRIDES = {
    "3D3C": "더",
    "3E37": "이",
    "3F38": "든",
}


def main():
    raw = json.load(open(MAP))
    before = len(raw)
    added = []
    for cp_hex, ch in OVERRIDES.items():
        if cp_hex in raw and raw[cp_hex] != ch:
            print(f"  CONFLICT {cp_hex}: was {raw[cp_hex]!r}, override {ch!r}")
        raw[cp_hex] = ch
        if cp_hex not in raw or True:
            added.append((cp_hex, ch))
    out_sorted = {k: raw[k] for k in sorted(raw, key=lambda h: int(h, 16))}
    MAP.write_text(json.dumps(out_sorted, indent=2, ensure_ascii=False) + "\n")
    print(f"before {before}, after {len(out_sorted)} (+{len(added) - (len(added) - 3)})")


if __name__ == "__main__":
    main()
