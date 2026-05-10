#!/usr/bin/env python3
"""Round-7 sentence-context labels."""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP = HERE / "codepoint_map.json"

ROUND7 = {
    "3770": "굉",  # 25 occ — 굉장한, 굉장하다
    "39D9": "렴",  # 28 occ — 베어보렴, 오렴, 따라오렴
    "3A5D": "멋",  # 28 occ — 멋진, 멋있어, 멋있다
    "3A6A": "며",  # 29 occ — 않으며, 비추며, 되며, 하며
    "3CAA": "앗",  # 27 occ — exclamation "앗!"
    "3DBB": "족",  # 29 occ — 부족했나, 만족, 폭주족
    "4039": "핑",  # 29 occ — 쇼핑하러, 핑크
}


def main():
    raw = json.load(open(MAP))
    before = len(raw)
    added = []
    for cp_hex, ch in ROUND7.items():
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
