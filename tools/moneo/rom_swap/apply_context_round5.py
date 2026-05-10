#!/usr/bin/env python3
"""Round-5 sentence-context labels. Each verified by corpus context,
LIS bracket constraint, and visual ROM-glyph match.

(0x3CFE 옛 was deferred: its atlas1 slot renders empty, so it's either
in atlas0/atlas2 or uses jamo composition. Need a separate path.)
"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP = HERE / "codepoint_map.json"

ROUND5 = {
    "373C": "겨",  # 59 occ — 이겨주지, 잠겨, 겨눠볼까
    "3757": "곳",  # 48 occ — 곳에도, 곳에서, 이 곳을
    "3837": "낚",  # 41 occ — 낚시, 낚아 올려, 낚이지만 (Magikarp)
    "39CC": "렇",  # 48 occ — 그렇게, 이렇게, 그렇지
    "39D7": "련",  # 50 occ — 홍련, 단련, 조련사
    "39DC": "렸",  # 49 occ — 기다렸어, 와버렸어, 진화해버렸어
    "3A28": "른",  # 47 occ — 어른들, 다른
    "3A58": "먼",  # 50 occ — 먼저, 구먼, 좋구먼
    "3A7B": "못",  # 53 occ — 못했던, 잠시도 못하겠지
    "3DBF": "좀",  # 45 occ — 포켓몬이 좀, 좀처럼
    "3DC2": "종",  # 41 occ — 종류, 신종
    "3DDC": "준",  # 49 occ — 해준다고, 와준다
    "3E74": "찾",  # 42 occ — 찾았어, 찾았다, 찾고 말했어
    "3FAC": "튼",  # 40 occ — 튼튼해서
    "404B": "행",  # 40 occ — 여행자, 유행, 통행
    "406E": "혼",  # 49 occ — 혼자, 약혼했어, 영혼
}


def main():
    raw = json.load(open(MAP))
    before = len(raw)
    added = []
    for cp_hex, ch in ROUND5.items():
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
