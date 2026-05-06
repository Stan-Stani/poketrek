#!/usr/bin/env python3
"""Render an arbitrary list of (page,idx) glyphs as a single zoomed-in
inspection sheet. Useful for batch labeling — feed it the hotlist from
find_unknowns.py and view the resulting PNG.

Usage:
  python3 tools/moneo/render_inspect.py F6,142 F2,241 ... -o /tmp/inspect.png
"""
from __future__ import annotations
import argparse
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

PALETTE = {
    0: (255, 255, 255), 1: (255, 255, 255), 2: (40, 40, 40),
    3: (160, 160, 160),
}


def render_glyph(rom, page, idx, scale=8):
    bs = transform_glyph(rom, page, idx)
    img = Image.new("RGB", (16, 16), "white")
    px = img.load()
    for k, (sx, sy) in enumerate([(0, 0), (8, 0), (0, 8), (8, 8)]):
        sub = bs[k * 32 : (k + 1) * 32]
        for r in range(8):
            for c in range(8):
                b = sub[r * 4 + c // 2]
                v = ((b >> 4) & 0xF) if (c & 1) else (b & 0xF)
                px[sx + c, sy + r] = PALETTE.get(v, (255, 0, 0))
    return img.resize((16 * scale, 16 * scale), Image.NEAREST)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("keys", nargs="+", help="F<p>,<i> ...")
    ap.add_argument("-o", "--out", default="/tmp/inspect.png")
    ap.add_argument("--scale", type=int, default=8)
    ap.add_argument("--cols", type=int, default=8)
    args = ap.parse_args()

    with open(ROM_PATH, "rb") as f:
        rom = f.read()
    gmap = json.loads(open(GMAP_PATH).read())["map"]

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Monaco.ttf", 14)
        han = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 18)
    except Exception:
        font = han = ImageFont.load_default()

    keys = args.keys
    cols = args.cols
    rows = (len(keys) + cols - 1) // cols
    GW, GH = 16 * args.scale + 12, 16 * args.scale + 36
    sheet = Image.new("RGB", (GW * cols, GH * rows), "white")
    draw = ImageDraw.Draw(sheet)
    for n, key in enumerate(keys):
        col, row = n % cols, n // cols
        p_str, i_str = key.lstrip("F").split(",")
        p, i = int(p_str), int(i_str)
        x0, y0 = col * GW, row * GH
        sheet.paste(render_glyph(rom, p, i, args.scale), (x0 + 6, y0 + 4))
        draw.text((x0 + 6, y0 + 16 * args.scale + 6),
                  key, fill="black", font=font)
        existing = gmap.get(key, "")
        if existing:
            draw.text((x0 + 6 + 70, y0 + 16 * args.scale + 6),
                      existing, fill="red", font=han)
        draw.rectangle((x0, y0, x0 + GW - 1, y0 + GH - 1), outline="lightgray")
    sheet.save(args.out)
    print(f"Wrote {args.out} ({sheet.size[0]}x{sheet.size[1]} px, {len(keys)} glyphs)")


if __name__ == "__main__":
    main()
