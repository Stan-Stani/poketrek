#!/usr/bin/env python3
"""Render a list of (page,idx) glyphs as ASCII block art.

Usage:
  python3 tools/moneo/render_ascii.py F6,142 F5,85 F2,241 ...
"""
import os, sys
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)
from decoded_blit import transform_glyph

ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
ROM_PATH = os.path.join(ROOT, "Pocket Monsters - LeafGreen (Korean).gba")
with open(ROM_PATH, "rb") as f:
    ROM = f.read()


def render(p, i):
    bs = transform_glyph(ROM, p, i)
    grid = [[0] * 16 for _ in range(16)]
    for k, (sx, sy) in enumerate([(0, 0), (8, 0), (0, 8), (8, 8)]):
        sub = bs[k * 32 : (k + 1) * 32]
        for r in range(8):
            for c in range(8):
                b = sub[r * 4 + c // 2]
                v = ((b >> 4) & 0xF) if (c & 1) else (b & 0xF)
                grid[sy + r][sx + c] = v
    rows = []
    for ry in range(0, 16, 2):
        chars = []
        for cx in range(16):
            top = grid[ry][cx] in (2, 3)
            bot = (ry + 1 < 16) and grid[ry + 1][cx] in (2, 3)
            chars.append("█" if top and bot else "▀" if top else "▄" if bot else " ")
        rows.append("".join(chars))
    return "\n".join(rows)


for arg in sys.argv[1:]:
    p_str, i_str = arg.lstrip("F").split(",")
    p, i = int(p_str), int(i_str)
    print(f"=== F{p},{i} ===")
    print(render(p, i))
    print()
