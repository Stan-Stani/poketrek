#!/usr/bin/env python3
"""Glyph-duplicates round 3: 6 alt-encoding labels + 3 blank-glyph controls.

Loosened the pixel-distance threshold from 4 to 8 and reviewed the
top-5 matches for each remaining unknown. Key insight: 0x3CFA, 0x40FE,
and 0x3FFB all have BLANK atlas glyphs — meaning they can't be
syllables at all, they must be text-formatting CONTROL bytes
(probably color/emphasis/font-switch markers since they appear
mid-word before adjectives/nouns).

  Committed labels:
    0x383C = 날   (revisits earlier rejection; the Magikarp Pokédex
                    context "수면을 [날]아 났다 미끄러지듯 잉어킹 움켜
                    잡는다" = "flying above the water surface, sliding,
                    grabs Magikarp" is decisive — bird-Pokemon entry.
                    Other 5 contexts fit as 날 = "day" or "fly".)
    0x4001 = 젤   (d=1 to labeled 0x3DAD=젤; essentially pixel-identical)
    0x38D8 = 탬   (d=2 to labeled 0x3F64=탬; near-identical pixels)
    0x3E4B = 죄   (d=2 to labeled 0x3DCF=죄. Context "보름달 [죄]면
                    흘러넘친다" is awkward in standard Korean (would
                    expect 쬐 = "shines") but font glyph IS 죄 — likely
                    font-compression alias)
    0x3739 = 켓   (d=4 to labeled 0x3F0F=켓; reversing earlier reject)
    0x3B66 = 받   (d=6 to 0x3ABF=받; sole context "{var:0F} [받]았다"
                    forms the canonical "received it" idiom)

  Blank-glyph CONTROLs (atlas slots near-empty; can't be syllables):
    0x3CFA — text-formatting marker; 8 occ appearing mid-word before
             adjectives ("[3CFA]희귀한 / [3CFA]많은 / [3CFA]완벽한 /
             [3CFA]챔피언이"). Blank glyph confirms control role,
             explains why no syllable context fit.
    0x40FE — text-formatting marker; 7 occ also mid-word
             ("[40FE]각도 / [40FE]통신 / [40FE]다른 / [40FE]공격").
             Blank glyph.
    0x3FFB — text-formatting marker; 5 occ mid-word
             ("[3FFB]심호흡 / [3FFB]희귀한 / [3FFB]그건"). Blank glyph.

This resolves 3 of the 6 "LIS-misanchored common short word" cluster
from StanNotes — they were never syllables at all.
"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP = HERE / "codepoint_map.json"
CONTROL = HERE / "control_codes.json"

LABELS = {
    "383C": "날",
    "4001": "젤",
    "38D8": "탬",
    "3E4B": "죄",
    "3739": "켓",
    "3B66": "받",
}

CONTROLS = {
    "3CFA": {
        "role": "CONTROL",
        "hypothesis": "Text-formatting marker (blank atlas glyph, mid-word position). 8 occurrences all immediately precede an adjective/noun ('[3CFA]희귀한', '[3CFA]많은', '[3CFA]완벽한', '[3CFA]챔피언이'). Sits in misanchored 옆-예 LIS window but is not a syllable — blank glyph rules it out.",
        "evidence_records": [999, 1075, 1699, 2061, 3152, 3916, 4067, 4212],
    },
    "40FE": {
        "role": "CONTROL",
        "hypothesis": "Text-formatting marker (blank atlas glyph, mid-word position). 7 occurrences all immediately precede a noun ('[40FE]각도', '[40FE]통신', '[40FE]다른', '[40FE]공격', '[40FE]하아'). Blank glyph rules out any syllable role.",
        "evidence_records": [2836, 2839, 2846, 3007, 4210, 5486, 6430],
    },
    "3FFB": {
        "role": "CONTROL",
        "hypothesis": "Text-formatting marker (blank atlas glyph, mid-word position). 5 occurrences mid-sentence preceding nouns/adjectives ('[3FFB]네', '[3FFB]심호흡', '[3FFB]어머', '[3FFB]희귀한', '[3FFB]그건'). Blank glyph rules out any syllable role.",
        "evidence_records": [1162, 1969, 2011, 2961, 3067],
    },
}


def main():
    raw = json.load(open(MAP))
    before_map = len(raw)
    added = 0
    for cp_hex, ch in LABELS.items():
        if cp_hex in raw:
            print(f"  CONFLICT in map {cp_hex}: was {raw[cp_hex]!r} -> {ch!r}")
            continue
        raw[cp_hex] = ch
        added += 1
    out_sorted = {k: raw[k] for k in sorted(raw, key=lambda h: int(h, 16))}
    MAP.write_text(json.dumps(out_sorted, indent=2, ensure_ascii=False) + "\n")
    print(f"codepoint_map: {before_map} -> {len(out_sorted)} (+{added})")

    controls = json.load(open(CONTROL))
    before_c = len(controls)
    added_c = 0
    for cp_hex, entry in CONTROLS.items():
        if cp_hex in controls:
            print(f"  CONFLICT in controls {cp_hex}: already present")
            continue
        controls[cp_hex] = entry
        added_c += 1
    CONTROL.write_text(json.dumps(controls, indent=2, ensure_ascii=False) + "\n")
    print(f"control_codes: {before_c} -> {len(controls)} (+{added_c})")


if __name__ == "__main__":
    main()
