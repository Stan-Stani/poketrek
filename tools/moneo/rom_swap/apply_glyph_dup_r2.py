#!/usr/bin/env python3
"""Glyph-duplicates round 2: 17 alt-encoding labels + 3 control aliases.

Re-ran scan_glyph_duplicates.py after glyph_id_r2 reduced the unknown
pool to 36 cps. It produced 20 pixel-match proposals (≤4 differing
pixels of 256) + 3 control aliases. After context verification:

  Committed labels (high context-fit):
    0x3EAD = 네   (9 occ; "yes/your" fits all 9 sentence contexts)
    0x3E34 = 찝   (2 occ; "찝찝" reduplication in same record)
    0x3C72 = 좌   (1 occ; "좌하고 쏘는" = "left-and shoots")
    0x3BAE = 산   (1 occ; "산 좀 잘 곳" = "mountain place to rest")
    0x37C1 = 까   (1 occ; "까 지금 밀지" = "until now don't push")
    0x3E93 = 랫   (4 occ; English loanword "rat" / character name)

  Committed labels (pixel-trust, neutral-to-weak context):
    0x3B7E = 똥   (2 occ; onomatopoeia "똥하고/뾰옹하고")
    0x3B65 = 쩌   (1 occ; "쩌렁/쩔" verb-stem partial)
    0x3FC9 = 빴   (1 occ; "빠르대/빨랐대" partial)
    0x40AC = 훗   (1 occ; sigh/laugh onomatopoeia)
    0x38EA = 몇   (1 occ; "몇 + 을" some-OBJ)
    0x395C = 랗   (1 occ; adjective-color suffix)
    0x3867 = 냅   (1 occ; "냅둬/냅다" partial)
    0x3E1A = 란   (1 occ; noun + 란)
    0x3EE0 = 컷   (1 occ; possible character/loan name)
    0x400E = 뢰   (2 occ; uncertain context, pixel-trust)
    0x399D = 뢰   (1 occ; uncertain context, pixel-trust)

  Rejected (pixel match but context clearly disagrees):
    0x383C → 넓   ("자 넓 시작할까" / "넓 나가" / "넓 시간이" don't read)
    0x3E4B → 죄   (context "보름달 [X]면 흘러넘친다" demands 쬐 "shines")
    0x3739 → 켓   ("방울소리가 켓 퍼졌다" / "어때 켓" don't fit)

  Control aliases (pixel match, all occurrences in binary tables):
    0x3A78 → CONTROL_ALIAS of 0x3942=듦
    0x3B78 → CONTROL_ALIAS of 0x3911=돌
    0x3783 → CONTROL_ALIAS of 0x378B=귀
"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP = HERE / "codepoint_map.json"
CONTROL = HERE / "control_codes.json"

LABELS = {
    "3EAD": "네",
    "3E34": "찝",
    "3C72": "좌",
    "3BAE": "산",
    "37C1": "까",
    "3E93": "랫",
    "3B7E": "똥",
    "3B65": "쩌",
    "3FC9": "빴",
    "40AC": "훗",
    "38EA": "몇",
    "395C": "랗",
    "3867": "냅",
    "3E1A": "란",
    "3EE0": "컷",
    "400E": "뢰",
    "399D": "뢰",
}

CONTROL_ALIASES = {
    "3A78": {
        "role": "CONTROL_ALIAS",
        "aliased_cp": "3942",
        "glyph_syllable": "듦",
        "hypothesis": "Glyph byte-identical to labeled 0x3942=듦 (≤4 pixel diff). Sole corpus occurrence in binary-table region (offset < 0x700000), not dialog.",
    },
    "3B78": {
        "role": "CONTROL_ALIAS",
        "aliased_cp": "3911",
        "glyph_syllable": "돌",
        "hypothesis": "Glyph byte-identical to labeled 0x3911=돌 (≤4 pixel diff). Sole corpus occurrence in binary-table region (offset < 0x700000), not dialog.",
    },
    "3783": {
        "role": "CONTROL_ALIAS",
        "aliased_cp": "378B",
        "glyph_syllable": "귀",
        "hypothesis": "Glyph byte-identical to labeled 0x378B=귀 (≤4 pixel diff). Sole corpus occurrence in binary-table region (offset < 0x700000), not dialog.",
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
    for cp_hex, entry in CONTROL_ALIASES.items():
        if cp_hex in controls:
            print(f"  CONFLICT in controls {cp_hex}: already present")
            continue
        controls[cp_hex] = entry
        added_c += 1
    CONTROL.write_text(json.dumps(controls, indent=2, ensure_ascii=False) + "\n")
    print(f"control_codes: {before_c} -> {len(controls)} (+{added_c})")


if __name__ == "__main__":
    main()
