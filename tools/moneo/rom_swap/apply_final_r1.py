#!/usr/bin/env python3
"""Final round: cluster reconciliation + control-byte classification +
long-tail visual labels.

Three parallel agents:
1. Cluster reconciliation (0x393x, 0x3A40+0x3AAB pair, 0x3D3F) —
   used already-labeled neighbors as anchors to triangulate the
   remaining cluster members.
2. Control-byte verification — confirmed glyph + position patterns
   for the suspected control cps. Also surfaced a key insight:
   **the ROM has duplicate glyph slots** (different cps render the
   same glyph). 0x408C is byte-identical to 0x4093=훗; 0x393A is
   byte-identical to 0x3929=둘.
3. Long-tail jamo r2 — agent-generated candidates for 155 cps with
   1-4 occurrences each, only 4 confident picks survived.

The 0x393A conflict (cluster agent said "번" from context, control
agent showed glyph is byte-identical to 둘) is resolved in favor of
the glyph: the ROM literally renders 둘 at this cp regardless of
whether 번 would have been more natural Korean. The map must reflect
what the ROM actually contains.

Labels applied (10 cps):
  0x3938 = 때   (26 occ — "V할 때" temporal: "할 때 입과", "꺼낼 때")
  0x393A = 둘   (67 occ — glyph-identical to 0x3929; "둘 이상", "둘 데려와")
  0x393C = 마   (18 occ — drink-verb stem: "주스 마시고")
  0x3A40 = 이   (38 occ — first syll of "이런")
  0x3AAB = 런   (10 occ — second syll of "이런")
  0x3D3F = 데   (26 occ — locational: "다양한 데 도전하고")
  0x4086 = 횟   (~3 occ — "횟수" count)
  0x3972 = 떼   (~2 occ — "떼지 말" don't take)
  0x3E44 = 쫓   (~2 occ — "쫓아낸다" chase away)
  0x3C9D = 씻   (~1 occ — washing verb)
"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP = HERE / "codepoint_map.json"

# LIS-override (cluster — known to break LIS bracket)
OVERRIDES = {
    "3938": "때",
    "393A": "둘",  # resolved in favor of glyph evidence over cluster agent's 번 guess
    "393C": "마",
    "3A40": "이",
    "3AAB": "런",
    "3D3F": "데",
}

# LIS-checked (long-tail — must fit current bracket)
LONGTAIL = {
    "3972": "떼",
    "3C9D": "씻",
    "3E44": "쫓",
    "4086": "횟",
}


def main():
    raw = json.load(open(MAP))
    before = len(raw)
    added = []

    for cp_hex, ch in {**OVERRIDES, **LONGTAIL}.items():
        if cp_hex in raw:
            if raw[cp_hex] != ch:
                print(f"  CONFLICT {cp_hex}: was {raw[cp_hex]!r} -> {ch!r}")
        raw[cp_hex] = ch
        added.append((cp_hex, ch))

    out_sorted = {k: raw[k] for k in sorted(raw, key=lambda h: int(h, 16))}
    MAP.write_text(json.dumps(out_sorted, indent=2, ensure_ascii=False) + "\n")
    print(f"before {before}, after {len(out_sorted)} (+{len(added)})")


if __name__ == "__main__":
    main()
