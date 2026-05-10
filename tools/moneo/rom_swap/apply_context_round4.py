#!/usr/bin/env python3
"""Round-4 sentence-context labels. Each verified by (a) corpus sentence
context, (b) LIS bracket constraint, (c) visual ROM glyph match against
the proposed PIL syllable in /tmp/poketrek_trace/single_unknown/.
"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP = HERE / "codepoint_map.json"

ROUND4 = {
    "3705": "갈",  # 72 occ — 번갈아서, 나갈 있지
    "3778": "군",  # 60 occ — 분이시군요, 강하군요, 같군요
    "383D": "남",  # 72 occ — 남아메리카, 남자였지, 남동생도, 남의
    "38BD": "님",  # 79 occ — 오박사님, 선장님, 손님들이
    "39C5": "런",  # 59 occ — 이런, 그런
    "3A45": "맞",  # 72 occ — 달맞이산, 맞다, 맞지, 맞히기는
    "3BC2": "섬",  # 70 occ — 홍련섬 (Cinnabar Island), 섬이라는 섬이
    "3C45": "십",  # 62 occ — 주십시오, 안녕하십니까
    "3C48": "싶",  # 80 occ — 잡으러 싶어서, 놀러 싶어, ~자 싶다네
    "3D1C": "왔",  # 60 occ — 들어왔지, 왔구나, 살아왔고
    "3ED2": "친",  # 73 occ — 친구랑, 친구들이, 지친
    "3FAB": "특",  # 64 occ — 특기야, 특기라서, 특별한
}


def main():
    raw = json.load(open(MAP))
    before = len(raw)
    added = []
    for cp_hex, ch in ROUND4.items():
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
