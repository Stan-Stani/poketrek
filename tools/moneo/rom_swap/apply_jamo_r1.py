#!/usr/bin/env python3
"""Jamo-structure picker round 1: agent-generated candidates.

PIL's top-8 candidate ranking is unreliable (sanity check 0% top-1 vs
ground truth). For the low-frequency tail, we had an agent visually
identify each ROM glyph's jamo composition (initial/medial/final
consonant) and propose syllable candidates from STRUCTURE rather than
PIL's pixel-overlap ranking, then verify against corpus context and
the LIS bracket.

22 labels yielded (out of 177 cps scoped). 23 confirmed atlas-hole
control bytes at xxFE/xxFF/xxF0/xxFB offsets (will never be characters).

All 22 verified to fit current LIS bracket — 0 overrides needed.

Notable picks:
  0x3FC1 = 팍  ("팍팍 봅시다" — adverbial onomatopoeia)
  0x3F4D = 킁  ("킁킁" — sniff sound)
  0x37D4 = 껴  ("느껴져서")
  0x3E2A = 쨌  ("어쨌든·난·간다")
  0x3A75 = 몫  ("한·몫을 슬·말")
  0x3CDF = 엥  ("엥? 일찍·뭐가")
  0x3F8E = 퇴  ("·퇴치한다")
  0x3857 = 넋  ("발차기·넋을 빼는")
"""
from __future__ import annotations
import json
from pathlib import Path

JAMO_R1 = {
    "3706": '갉',
    "3784": '궁',
    "37D4": '껴',
    "3857": '넋',
    "3A4E": '맷',
    "3A75": '몫',
    "3A97": '뭉',
    "3A98": '뭉',
    "3B7A": '뽑',
    "3C1A": '숫',
    "3C50": '쌌',
    "3CDF": '엥',
    "3D1B": '왓',
    "3DE7": '쥐',
    "3E04": '즉',
    "3E2A": '쨌',
    "3E51": '쭉',
    "3F48": '큭',
    "3F4D": '킁',
    "3F8E": '퇴',
    "3FC1": '팍',
    "4048": '햅',
}
# 22 entries


HERE = Path(__file__).resolve().parent
MAP = HERE / "codepoint_map.json"


def main():
    raw = json.load(open(MAP))
    before = len(raw)
    added = []
    for cp_hex, ch in JAMO_R1.items():
        cp_hex = cp_hex.upper()
        if cp_hex in raw:
            if raw[cp_hex] != ch:
                print(f"  CONFLICT {cp_hex}: have {raw[cp_hex]!r}, prop {ch!r}")
            continue
        raw[cp_hex] = ch
        added.append((cp_hex, ch))
    out_sorted = {k: raw[k] for k in sorted(raw, key=lambda h: int(h, 16))}
    MAP.write_text(json.dumps(out_sorted, indent=2, ensure_ascii=False) + "\n")
    print(f"before {before}, after {len(out_sorted)} (+{len(added)})")


if __name__ == "__main__":
    main()
