#!/usr/bin/env python3
"""Glyph-identification round 2: 1 syllable label + 4 control classifications.

After 39 truly-unknown codepoints remained post-final-pass, examined the
top-frequency survivors and locked in:

  0x400A = 틱  — alt-encoded syllable forming "조이스틱" (joystick) in
                 wireless-adapter Korean error messages.
                 Confirmed via 4/5 corpus contexts:
                   "조이스[400A]의 ··· 중지했습니다"
                   "조이스[400A]과의 ··· 성"
                   "조이스[400A]을 있습니다"
                   "조이스[400A]으로부터의"
                 LIS bracket (폴-폼) is wrong; this is a known alt-encoding
                 pattern for common syllables.

  CONTROL bytes (no syllable role; sentence-final with no following
  content, or item-counter glyph):
    0x3DFF — sentence terminator; 5/5 occurrences sentence-final
             ("아우 [3DFF]", "버튼 [3DFF]", "이상한 [3DFF]" etc.)
    0x3BFF — sentence terminator; 5/5 occurrences sentence-final
             ("배짱이 [3BFF]", "녀석들은 [3BFF]" etc.)
    0x3CFF — sentence terminator; 3/3 occurrences sentence-final
             ("취소된었습니다 [3CFF]", "대전을 [3CFF]" etc.)
    0x40FC — inventory-counter glyph; 3/3 in "{item} [40FC] ··· 개"
             ("기술머신 [40FC] 개", "삐삐 [40FC] 개")
"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP = HERE / "codepoint_map.json"
CONTROL = HERE / "control_codes.json"

LABELS = {
    "400A": "틱",
}

CONTROLS = {
    "3DFF": {
        "role": "CONTROL",
        "hypothesis": "Sentence/dialog terminator. All 5 occurrences are sentence-final with no following text ('아우 [3DFF]', '버튼 [3DFF]', '이상한 [3DFF]', '아이템 [3DFF]', '말똑을 두고 [3DFF]').",
        "evidence_records": [563, 1430, 5847, 6994, 7000],
    },
    "3BFF": {
        "role": "CONTROL",
        "hypothesis": "Sentence/dialog terminator. All 5 occurrences are sentence-final with no following text ('하 싶진 [3BFF]', '녀석들은 [3BFF]', '배짱이 [3BFF]', '웅님만큼은 [3BFF]', '있다고 슬 [3BFF]').",
        "evidence_records": [660, 1167, 1542, 2184, 2673],
    },
    "3CFF": {
        "role": "CONTROL",
        "hypothesis": "Sentence/dialog terminator. All 3 occurrences are sentence-final with no following text ('취소된었습니다 [3CFF]', '대전을 [3CFF]', '곳 또 [3CFF]'). Sits in same bracket window as the misanchored 옆-예 zone (0x3CFA/0x3CFE family) but with control-role evidence.",
        "evidence_records": [6159, 6919, 6921],
    },
    "40FC": {
        "role": "CONTROL",
        "hypothesis": "Inventory-quantity glyph (multiplication/counter separator). 3/3 occurrences in inventory display pattern '{item} [40FC] ··· 개': '기술머신 [40FC] 개' (x2), '삐삐 [40FC] 개'.",
        "evidence_records": [5604, 5605, 5628],
    },
}


def main():
    raw = json.load(open(MAP))
    before_map = len(raw)
    for cp_hex, ch in LABELS.items():
        if cp_hex in raw and raw[cp_hex] != ch:
            print(f"  CONFLICT in map {cp_hex}: was {raw[cp_hex]!r} -> {ch!r}")
        raw[cp_hex] = ch
    out_sorted = {k: raw[k] for k in sorted(raw, key=lambda h: int(h, 16))}
    MAP.write_text(json.dumps(out_sorted, indent=2, ensure_ascii=False) + "\n")
    print(f"codepoint_map: {before_map} -> {len(out_sorted)} (+{len(LABELS)})")

    controls = json.load(open(CONTROL))
    before_c = len(controls)
    for cp_hex, entry in CONTROLS.items():
        if cp_hex in controls:
            print(f"  CONFLICT in controls {cp_hex}: already present")
            continue
        controls[cp_hex] = entry
    CONTROL.write_text(json.dumps(controls, indent=2, ensure_ascii=False) + "\n")
    print(f"control_codes: {before_c} -> {len(controls)} (+{len(CONTROLS)})")


if __name__ == "__main__":
    main()
