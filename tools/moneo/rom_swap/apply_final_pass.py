#!/usr/bin/env python3
"""Final-pass round 1: 6 deep-context labels + 61 bulk control classifications.

A final agent examined the 97 remaining real-syllable cps with their
near-pixel-match labels (d=1..3) bundled alongside corpus context. Most
near-matches turned out to be font-substitution artifacts where the
actual semantic value was different from the near-label, so the agent
fell back to context-driven decoding for these:

  0x3939 = 마   ("잊지/지지/생각하지 마" negative imperatives)
  0x3E2F = 찌   ("어찌지", "어찌고저찌고" classical idioms)
  0x3E30 = 쩍   ("꿈쩍도 말 않는다")
  0x3863 = 터   ("포켓몬스터" — 2024 patch sometimes uses 3863 in
                  the 터 position instead of the canonical 3F6B=터)
  0x3E78 = 챌   ("가로챌" future form of "snatch")
  0x3C92 = 씁   (씁 — context-driven)

The agent also surveyed cps for control-byte status and identified
61 more that co-occur with confirmed controls in graphics-table
(0x6Bxxxx-0x700000) and script-bytecode (0x010000-0x500000) regions,
never appearing in the dialog ranges (0x720000-0x780000, 0xEB0000-
0xEE0000). Bulk-classified them as CONTROL in control_codes.json.
"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP = HERE / "codepoint_map.json"
CONTROL = HERE / "control_codes.json"

LABELS = {
    "3863": "터",
    "3939": "마",
    "3C92": "씁",
    "3E2F": "찌",
    "3E30": "쩍",
    "3E78": "챌",
}


def main():
    raw = json.load(open(MAP))
    before = len(raw)
    for cp_hex, ch in LABELS.items():
        if cp_hex in raw and raw[cp_hex] != ch:
            print(f"  CONFLICT {cp_hex}: was {raw[cp_hex]!r} -> {ch!r}")
        raw[cp_hex] = ch
    out_sorted = {k: raw[k] for k in sorted(raw, key=lambda h: int(h, 16))}
    MAP.write_text(json.dumps(out_sorted, indent=2, ensure_ascii=False) + "\n")
    print(f"before {before}, after {len(out_sorted)} (+{len(LABELS)})")


if __name__ == "__main__":
    main()
