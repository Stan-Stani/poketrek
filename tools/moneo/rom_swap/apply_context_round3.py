#!/usr/bin/env python3
"""Round-3 sentence-context labels. Each verified by (a) corpus sentence
context, (b) LIS bracket constraint, (c) visual ROM glyph match against
the proposed PIL syllable in /tmp/poketrek_trace/single_unknown/.
"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP = HERE / "codepoint_map.json"

ROUND3 = {
    "393F": "든",  # 96 occ — 만든, 언제든지, 모든, 바쁘거든
    "39C7": "럼",  # 100 occ — 모처럼, 그럼, 처럼
    "3C3D": "승",  # 164 occ — 승부, 승부야말로
    "3CAB": "았",  # 105 occ — 알았어, 잡았다고, 받았다, 살았어
    "3D0B": "올",  # 91 occ — 걸어올, 찾아올, 올라가, 뛰어올라가는
    "3D85": "잘",  # 86 occ — 재정비하고 잘게, 잘라서
    "3DDD": "줄",  # 84 occ — 도와줄, 줄게, 갚아줄, 귀여워해줄
}


def main():
    raw = json.load(open(MAP))
    before = len(raw)
    added = []
    for cp_hex, ch in ROUND3.items():
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
