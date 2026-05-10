#!/usr/bin/env python3
"""Apply round-2 sentence-context labels: 9 high-frequency unknowns
deduced by reading their corpus occurrences in
/tmp/poketrek_trace/decode_by_context.txt and visually verified against
the ROM glyph at /tmp/poketrek_trace/single_unknown/cp_XXXX.png.

Each entry was confirmed by:
  - LIS bracket constraint (predicted syllable inside the candidate window)
  - corpus context (the syllable forms valid Korean in every example)
  - visual match between ROM glyph and the proposed PIL candidate
"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP = HERE / "codepoint_map.json"

ROUND2 = {
    "3710": "같",  # 156 occ — 매일같이, 같이 있어
    "373A": "겠",  # 136 occ — 좋겠다, 해야겠구나
    "375A": "과",  # 106 occ — 트레이너들과, 포켓몬과
    "3D15": "와",  # 138 occ — 도와주세요
    "3D61": "을",  # 1287 occ — 포켓몬을, 동굴을, 않을 (object marker)
    "3DC5": "좋",  # 180 occ — 좋다고, 좋아, 좋은
    "3E3F": "쪽",  # 136 occ — directional 쪽
    "3E8D": "체",  # 127 occ — 포켓몬체육관, 정체
    "3FAE": "틀",  # 111 occ — 틀림없어, 배틀
}


def main():
    raw = json.load(open(MAP))
    before = len(raw)
    added = []
    skipped = []
    for cp_hex, ch in ROUND2.items():
        if cp_hex in raw:
            if raw[cp_hex] != ch:
                print(f"  CONFLICT {cp_hex}: have {raw[cp_hex]!r}, want {ch!r}")
            skipped.append(cp_hex)
            continue
        raw[cp_hex] = ch
        added.append((cp_hex, ch))

    out_sorted = {k: raw[k] for k in sorted(raw, key=lambda h: int(h, 16))}
    MAP.write_text(json.dumps(out_sorted, indent=2, ensure_ascii=False) + "\n")
    print(f"before {before}, after {len(out_sorted)} (+{len(added)})")
    for cp_hex, ch in added:
        print(f"  + {cp_hex} -> {ch}")
    if skipped:
        print(f"already present: {skipped}")


if __name__ == "__main__":
    main()
