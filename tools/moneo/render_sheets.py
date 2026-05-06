#!/usr/bin/env python3
"""Render all 6 Korean font pages as 16x16 grids of labeled glyphs.

Output: tools/moneo/sheets/page{1..6}.png (one per font page).

Each cell shows the 48x48 glyph at scale 3, the (page, idx) decimal index, and
the current Hangul label from glyph-map.json if known. Use the sheets to
visually verify or re-label glyph-map.json entries.

Run: python3 tools/moneo/render_sheets.py
"""
from __future__ import annotations
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)
from decoded_blit import transform_glyph

ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
ROM_PATH = os.path.join(ROOT, "Pocket Monsters - LeafGreen (Korean).gba")
GMAP_PATH = os.path.join(_THIS_DIR, "glyph-map.json")
OUT_DIR = os.path.join(_THIS_DIR, "sheets")

PALETTE = {
    0: (255, 255, 255), 1: (220, 220, 220), 2: (40, 40, 40), 3: (100, 100, 100),
    4: (180, 80, 80), 5: (80, 200, 80), 6: (80, 80, 200), 7: (200, 200, 80),
    8: (200, 80, 200), 9: (80, 200, 200), 10: (255, 128, 0), 11: (128, 0, 128),
    12: (128, 128, 0), 13: (0, 128, 128), 14: (255, 200, 200), 15: (50, 50, 50),
}


def render_glyph(rom: bytes, page: int, idx: int, scale: int = 3) -> Image.Image:
    bytes_128 = transform_glyph(rom, page, idx)
    img = Image.new("RGB", (16, 16), "white")
    px = img.load()
    for k, (sx, sy) in enumerate([(0, 0), (8, 0), (0, 8), (8, 8)]):
        sub_bytes = bytes_128[k * 32 : (k + 1) * 32]
        for r in range(8):
            for c in range(8):
                b = sub_bytes[r * 4 + c // 2]
                v = ((b >> 4) & 0xF) if (c & 1) else (b & 0xF)
                px[sx + c, sy + r] = PALETTE[v]
    return img.resize((16 * scale, 16 * scale), Image.NEAREST)


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(ROM_PATH, "rb") as f:
        rom = f.read()
    with open(GMAP_PATH) as f:
        gmap = json.load(f)["map"]

    try:
        font_idx = ImageFont.truetype("/System/Library/Fonts/Monaco.ttf", 9)
        font_han = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 14)
    except Exception:
        font_idx = font_han = ImageFont.load_default()

    GW, GH = 80, 80
    cols, rows = 16, 16
    for page in range(0, 8):  # 0..7 (page 0 = base font, 1-6 = F1-F6, 7 = extended)
        sheet = Image.new("RGB", (GW * cols, GH * rows), "white")
        draw = ImageDraw.Draw(sheet)
        for i in range(256):
            col = i % 16
            row = i // 16
            x0 = col * GW
            y0 = row * GH
            sheet.paste(render_glyph(rom, page, i, scale=3), (x0 + 4, y0 + 4))
            draw.text((x0 + 56, y0 + 4), f"{i:>3}", fill="gray", font=font_idx)
            han = gmap.get(f"F{page},{i}", "")
            if han:
                draw.text((x0 + 56, y0 + 18), han, fill="black", font=font_han)
            draw.rectangle((x0, y0, x0 + GW - 1, y0 + GH - 1), outline="lightgray")
        out = os.path.join(OUT_DIR, f"page{page}.png")
        sheet.save(out)
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
