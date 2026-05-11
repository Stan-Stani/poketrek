#!/usr/bin/env python3
"""Reconciliation round 2: more LIS-override labels via deeper context.

Reconcile r1 picked the obvious 5; r2 went deeper on the 76 cps with
≥5 occurrences and read 15 contexts per cp + visually cross-checked
the ROM glyph against the picker sheets.

13 labels covering 485 occurrences (~25% of remaining unknown text):

  0x3E3D = 곳  (213 occ — place noun: "이런 곳에서도")
  0x3D39 = 그  ( 67 occ — demonstrative)
  0x3D38 = 든  ( 39 occ — "마음에 든다" suit/like idiom)
  0x3968 = 디  ( 29 occ — "어디" interrogative)
  0x3828 = 끔  ( 26 occ — "가끔씩")
  0x3C98 = 씩  ( 24 occ — "마리씩/한번씩")
  0x3971 = 떻  ( 21 occ — "어떻게" how-interrogative)
  0x3C3A = 잘  ( 17 occ — adverb "well")
  0x3932 = 뒤  ( 14 occ — "뒤집어쓰고")
  0x3942 = 듦  ( 14 occ — verb conjugation form)
  0x3D06 = 옛  ( 11 occ — "옛날부터")
  0x3716 = 갤  (  5 occ — "씨갤럽" SS Anne)
  0x3E52 = 짝  (  5 occ — "혀가 짝짝")

Skips of note: 0x3E37 (88, polysemous), 0x4038 (111, sentence-final
filler), 0x3D3C (76, polysemous), 0x3A40 (38, "맙소사" cluster part),
0x3F40 (33, "OO 본사" modifier). The 0x393x family is a tight cluster
of verb-ending glyphs that needs joint reconciliation.

Confirmed control-byte cps (blank glyphs, will never be labeled):
0x3BFE, 0x3CFA, 0x3CFE, 0x3DFE, 0x3DFF, 0x3EFE, 0x3FFB, 0x3FFE,
0x3FFF, 0x40FE.
"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP = HERE / "codepoint_map.json"

OVERRIDES = {
    "3716": "갤",
    "3828": "끔",
    "3932": "뒤",
    "3942": "듦",
    "3968": "디",
    "3971": "떻",
    "3C3A": "잘",
    "3C98": "씩",
    "3D06": "옛",
    "3D38": "든",
    "3D39": "그",
    "3E3D": "곳",
    "3E52": "짝",
}


def main():
    raw = json.load(open(MAP))
    before = len(raw)
    added, conflicts = [], []
    for cp_hex, ch in OVERRIDES.items():
        cp_hex = cp_hex.upper()
        if cp_hex in raw:
            if raw[cp_hex] != ch:
                conflicts.append((cp_hex, raw[cp_hex], ch))
                raw[cp_hex] = ch
        else:
            raw[cp_hex] = ch
            added.append((cp_hex, ch))
    out_sorted = {k: raw[k] for k in sorted(raw, key=lambda h: int(h, 16))}
    MAP.write_text(json.dumps(out_sorted, indent=2, ensure_ascii=False) + "\n")
    print(f"before {before}, after {len(out_sorted)} (+{len(added)} overrides)")
    if conflicts:
        for c in conflicts:
            print(f"  CONFLICT {c[0]}: was {c[1]!r} -> {c[2]!r}")


if __name__ == "__main__":
    main()
