#!/usr/bin/env python3
"""Apply round 1 of glyph-duplicate scan results.

Scan compared every remaining-unknown cp's decoded 16x16 ROM glyph
against every labeled cp's glyph at the pixel level. Unknown cps with
EXACT pixel matches against a labeled glyph are classified by where
their corpus occurrences fall:

  - Dialog region (offset >= 0x700000): alt-encoding -> apply as label
  - Binary table region (offset <  0x700000): control alias -> document
  - Mixed: skip for review

This recovers 28 alt-encoding labels + 22 control aliases in one batch.
"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP = HERE / "codepoint_map.json"
CONTROL = HERE / "control_codes.json"

ALT_ENCODINGS = {
    "373B": '갱',
    "3747": '걸',
    "387B": '늠',
    "3897": '늠',
    "38AD": '놀',
    "3915": '듭',
    "395F": '랜',
    "3991": '될',
    "3999": '돌',
    "3A9C": '함',
    "3AA5": '돌',
    "3AD2": '밸',
    "3ADF": '빗',
    "3B37": '봄',
    "3B3B": '복',
    "3B3E": '봄',
    "3C39": '술',
    "3EB5": '춤',
    "3F07": '켰',
    "3F34": '킁',
    "3F3E": '될',
    "3F7A": '랩',
    "3F9A": '롱',
    "3FAD": '롤',
    "405E": '앵',
    "40A3": '휩',
    "40AB": '훔',
    "40B2": '훔',
}
# 28 entries

CONTROL_ALIASES = {
    "3749": {"aliased_cp": "3735", "glyph_syllable": '겐'},
    "388C": {"aliased_cp": "3877", "glyph_syllable": '녹'},
    "3978": {"aliased_cp": "39BB", "glyph_syllable": '랫'},
    "397F": {"aliased_cp": "3997", "glyph_syllable": '뜬'},
    "398A": {"aliased_cp": "3911", "glyph_syllable": '돌'},
    "3A4C": {"aliased_cp": "39B9", "glyph_syllable": '램'},
    "3AD1": {"aliased_cp": "39BD", "glyph_syllable": '랭'},
    "3B8C": {"aliased_cp": "3B7A", "glyph_syllable": '뽑'},
    "3C7F": {"aliased_cp": "3C8C", "glyph_syllable": '쓱'},
    "3C82": {"aliased_cp": "3C91", "glyph_syllable": '씀'},
    "3D6F": {"aliased_cp": "3D50", "glyph_syllable": '윌'},
    "3E98": {"aliased_cp": "3E8D", "glyph_syllable": '체'},
    "3F14": {"aliased_cp": "3F04", "glyph_syllable": '컴'},
    "3F83": {"aliased_cp": "39E3", "glyph_syllable": '록'},
    "401A": {"aliased_cp": "3942", "glyph_syllable": '듦'},
    "402D": {"aliased_cp": "3DBC", "glyph_syllable": '존'},
    "4045": {"aliased_cp": "3CB1", "glyph_syllable": '앤'},
    "4046": {"aliased_cp": "3CB2", "glyph_syllable": '앨'},
    "405C": {"aliased_cp": "4048", "glyph_syllable": '햅'},
    "405D": {"aliased_cp": "3CDE", "glyph_syllable": '엣'},
    "4069": {"aliased_cp": "3CB1", "glyph_syllable": '앤'},
    "4083": {"aliased_cp": "40BB", "glyph_syllable": '흰'},
}


def main():
    raw = json.load(open(MAP))
    before = len(raw)
    added = []
    for cp_hex, ch in ALT_ENCODINGS.items():
        if cp_hex in raw and raw[cp_hex] != ch:
            print(f"  CONFLICT {cp_hex}: was {raw[cp_hex]!r} -> {ch!r}")
        raw[cp_hex] = ch
        added.append((cp_hex, ch))
    out_sorted = {k: raw[k] for k in sorted(raw, key=lambda h: int(h, 16))}
    MAP.write_text(json.dumps(out_sorted, indent=2, ensure_ascii=False) + "\n")

    # Merge control aliases into control_codes.json
    controls = json.load(open(CONTROL))
    for cp_hex, info in CONTROL_ALIASES.items():
        controls[cp_hex] = {
            "role": "CONTROL_ALIAS",
            "aliased_cp": info["aliased_cp"],
            "glyph_syllable": info["glyph_syllable"],
            "hypothesis": "Exact pixel match to labeled cp; corpus "
                          "occurrences only in binary tables (offset "
                          "< 0x700000), not dialog.",
        }
    CONTROL.write_text(json.dumps(controls, indent=2, ensure_ascii=False))

    print(f"before {before}, after {len(out_sorted)} (+{len(added)} alt-encodings)")
    print(f"control_codes.json: {len(controls)} entries (+{len(CONTROL_ALIASES)} aliases)")


if __name__ == "__main__":
    main()
