#!/usr/bin/env python3
"""Round-6 sentence-context labels."""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP = HERE / "codepoint_map.json"

ROUND6 = {
    "370E": "갖",  # 34 occ — 갖고, 갖고 싸울
    "373F": "견",  # 31 occ — 발견한다, 발견했다, 참견을
    "3861": "넣",  # 31 occ — 도구를 넣었다
    "38BA": "닌",  # 34 occ — 닌자, 닌자마스터
    "393E": "득",  # 39 occ — 가득이라네, 가득하구나
    "3A46": "맡",  # 37 occ — 맡기마, 맡아줘, 맡길 수 있어
    "3ADE": "법",  # 38 occ — 제법, 방법을
    "3BBF": "설",  # 31 occ — 전설의, 설마, 전설
    "3F49": "큰",  # 35 occ — 큰버섯, 큰일이라는, 큰 ~ 작은
    "405F": "혀",  # 35 occ — 전혀, 잡혀, 밝혀진
    "4067": "형",  # 32 occ — 형이, 인형, 형태, 봉제인형
}


def main():
    raw = json.load(open(MAP))
    before = len(raw)
    added = []
    for cp_hex, ch in ROUND6.items():
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
