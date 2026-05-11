#!/usr/bin/env python3
"""Polysemous resolution round 1: majority-rule labels for the 22 cps
flagged as polysemous by reconcile r2/r3.

Insight: prior rounds flagged these as "different syllable per context"
but reconcile r3 demonstrated that polysemous codepoints are usually
just ALTERNATE ENCODINGS of common Korean syllables — the patch uses
multiple cps for one syllable (different glyph variants for context).
Applying a majority-fit syllable gives best overall readability even if
~30% of occurrences read slightly off.

22 LIS-override labels (~672 occurrences):

  0x3F40 = 실  (32 occ — "실프 본사" Silph Co.)
  0x3B3F = 절  (32 occ — "절반을 회복한다" move boilerplate)
  0x3FFE = 혼  (11 occ — "혼란 상태")
  0x3E3A = 루  (30 occ — "겨루다" compete)
  0x393B = 마  (27 occ — "마비" status condition)
  0x3A3D = 또  (58 occ — adverbial "again")
  0x3CFE = 정  (47 occ — "정말" intensifier first syll)
  0x3E40 = 시  (61 occ)
  0x3E39 = 문  (59 occ)
  0x3E38 = 요  (48 occ — sentence-final polite)
  0x3E3B = 쭉, 0x3E3E = 쉽, 0x3B40 = 자, 0x3839 = 잘, 0x3F39 = 찍
  0x3EAB = 네, 0x3EFE = 역, 0x3BFA = 그, 0x3BAD = 이, 0x3BFE = 잘
  0x4037 = 신, 0x3937 = 잘

Known lower-confidence picks (may produce minor mis-decodes):
  - 0x3E38=요 is generic; some non-요 contexts will read off.
  - 0x3A3D=또 doesn't fit "씨갤럽 X호" boat-number contexts.
  - Three cps mapping to 잘 (0x3839, 0x3BFE, 0x3937) are likely
    alt-encodings — could be differentiated as 막/꼭 with more analysis.
"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP = HERE / "codepoint_map.json"

OVERRIDES = {
    "3839": "잘",
    "393B": "마",
    "3937": "잘",
    "3A3D": "또",
    "3B3F": "절",
    "3B40": "자",
    "3BAD": "이",
    "3BFA": "그",
    "3BFE": "잘",
    "3CFE": "정",
    "3E38": "요",
    "3E39": "문",
    "3E3A": "루",
    "3E3B": "쭉",
    "3E3E": "쉽",
    "3E40": "시",
    "3EAB": "네",
    "3EFE": "역",
    "3F39": "찍",
    "3F40": "실",
    "3FFE": "혼",
    "4037": "신",
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
