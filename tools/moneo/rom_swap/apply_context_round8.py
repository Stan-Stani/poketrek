#!/usr/bin/env python3
"""Round-8 sentence-context labels."""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP = HERE / "codepoint_map.json"

ROUND8 = {
    "386B": "녀",  # 59 occ — 녀석, 녀석들이, 녀석이군
    "3995": "뜨",  # 50 occ — 뜨거운, 시골뜨기, 떨어뜨려
    "38B2": "능",  # 36 occ — 능력, 재능, 특수능력, 초능력
    "391E": "됐",  # 35 occ — 됐어, 됐는데, 됐습니다
    "3B11": "봐",  # 51 occ — 봐라, 낚아올려봐, 바위를 봐라
    "3B4C": "빠",  # 51 occ — 빠져나가다, 재빠른, 빠르게
    "3C8E": "쓸",  # 37 occ — 쓸 수 있게, 쓸쓸하지
    "3DB7": "졌",  # 77 occ — 강해졌나, 졌잖아, 졌군
    "3F11": "켜",  # 36 occ — 지켜주면, 들켜버렸네, 배틀시켜
    "3FE9": "편",  # 34 occ — 편리하지, 건너편, 편해서
    "4053": "험",  # 43 occ — 위험, 시험, 위험합니다
    "4088": "효",  # 42 occ — 효과, 효원, 특수효력
}


def main():
    raw = json.load(open(MAP))
    before = len(raw)
    added = []
    for cp_hex, ch in ROUND8.items():
        if cp_hex in raw:
            if raw[cp_hex] != ch:
                print(f"  CONFLICT {cp_hex}: have {raw[cp_hex]!r}, want {ch!r}")
            continue
        raw[cp_hex] = ch
        added.append((cp_hex, ch))

    out_sorted = {k: raw[k] for k in sorted(raw, key=lambda h: int(h, 16))}
    MAP.write_text(json.dumps(out_sorted, indent=2, ensure_ascii=False) + "\n")
    print(f"before {before}, after {len(out_sorted)} (+{len(added)})")
    for cp_hex, ch in added:
        print(f"  + {cp_hex} -> {ch}")


if __name__ == "__main__":
    main()
