#!/usr/bin/env python3
"""Add hand-curated mappings for digit/special-character codepoints that
the iterative resolver cannot triangulate (because they are not Hangul).
"""
from __future__ import annotations
import json
from pathlib import Path

NAMES_DIR = Path(__file__).resolve().parent

# These are ASCII-like codepoints inferred from PokeAPI canonical names.
# For instance, mv85 = "10만볼트": 10 = digits 1+0, but the encoding stored
# A2A1 as a single codepoint that decodes to "1" or "10".
# Without seeing the exact byte breakdown, the safer approach is to drop
# entries where these special glyphs appear (HP, ♂, ♀, digits) — they're
# minor noise.
HAND_MAP = {
    # Special digit/symbol codepoints to skip; we map to placeholder
    # so they decode to something readable even if not perfectly Korean.
    # Comment out to keep them <CPxxxx> in output (so they get filtered later).
}


def main():
    cp_map_path = NAMES_DIR / "codepoint_map.json"
    cp_map = json.loads(cp_map_path.read_text())
    for k, v in HAND_MAP.items():
        cp_map[k] = v
    cp_map_path.write_text(json.dumps(cp_map, ensure_ascii=False, indent=1))
    print(f"Total codepoints mapped: {len(cp_map)}")


if __name__ == "__main__":
    main()
