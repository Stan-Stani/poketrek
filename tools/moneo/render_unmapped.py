#!/usr/bin/env python3
"""Render only the unmapped (in attributed records) glyphs as a focused
sheet so a multimodal viewer can label them visually.

Cell layout: 8 columns × N rows, each cell 96×96 px. Glyph rendered
24× upscaled (16x16 -> 384x384? no -- scale=4 -> 64x64) with the
'(p,i) ×count' label below. Sorted by descending count.
"""
from __future__ import annotations
import argparse
import json
import os
import struct
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROM_PATH = ROOT / "Pocket Monsters - LeafGreen (Korean).gba"
GMAP_PATH = Path(__file__).resolve().parent / "glyph-map.json"
LIVE_PATH = Path(__file__).resolve().parent / "corpus.ko.live.json"
STATIC_PATH = ROOT / "app/src/main/assets/moneo/corpus.ko.json"
AREA_PATH = Path(__file__).resolve().parent / "map_area_index.json"
OUT_DIR = Path(__file__).resolve().parent / "sheets"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from decoded_blit import transform_glyph  # type: ignore
from PIL import Image, ImageDraw, ImageFont  # type: ignore

# Match the source font palette (values 0-3 are grayscale, 4+ are markup colors).
# Render text-ink pixels (2, 3) as black; background (0, 1) as white.
PALETTE = {
    0: (255, 255, 255), 1: (220, 220, 220),
    2: (0, 0, 0), 3: (60, 60, 60),
    **{i: (255, 80, 80) for i in range(4, 16)},  # markup -> red so we can spot it
}


def render_glyph(rom: bytes, page: int, idx: int, scale: int = 4):
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


def collect_unmapped(rom: bytes) -> list[tuple[str, int]]:
    """Return sorted list of (key, count) for glyphs unmapped in glyph-map.json
    that occur in resolved-area records."""
    gm = json.loads(GMAP_PATH.read_text())["map"]
    mai = json.loads(AREA_PATH.read_text())
    resolved = set()
    for info in mai.get("resolved_areas", {}).values():
        for rid in info.get("recIds", []):
            resolved.add(rid)
    all_records = {}
    for r in json.loads(LIVE_PATH.read_text())["records"]:
        all_records[r["id"]] = r
    for r in json.loads(STATIC_PATH.read_text())["records"]:
        all_records.setdefault(r["id"], r)

    counts: Counter[str] = Counter()
    for rid in resolved:
        rec = all_records.get(rid)
        if not rec:
            continue
        off = rec.get("offset")
        if off is None:
            continue
        i = off
        while i < min(off + 500, len(rom)):
            b = rom[i]
            if b == 0xFF:
                break
            if b == 0xFE:
                i += 1
                continue
            if b in (0xFA, 0xFB):
                i += 1
                continue
            if b in (0xFC, 0xFD) and i + 1 < len(rom):
                i += 2
                continue
            if 0xF1 <= b <= 0xF6 and i + 1 < len(rom):
                key = f"F{b - 0xF0},{rom[i+1]}"
                if key not in gm:
                    counts[key] += 1
                i += 2
                continue
            key = f"F0,{b}"
            if key not in gm:
                counts[key] += 1
            i += 1
    return counts.most_common()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--top", type=int, default=80)
    ap.add_argument("--cols", type=int, default=8)
    ap.add_argument("--scale", type=int, default=4)
    args = ap.parse_args()
    OUT_DIR.mkdir(exist_ok=True)
    rom = ROM_PATH.read_bytes()

    unmapped = collect_unmapped(rom)
    if not unmapped:
        print("No unmapped glyphs in resolved-area records.")
        return 1
    print(f"{len(unmapped)} distinct unmapped, "
          f"{sum(c for _, c in unmapped)} total occurrences. "
          f"Rendering top {min(args.top, len(unmapped))}.")
    take = unmapped[: args.top]

    cell_w = 16 * args.scale + 8
    cell_h = 16 * args.scale + 24
    cols = args.cols
    rows = (len(take) + cols - 1) // cols
    sheet = Image.new("RGB", (cell_w * cols, cell_h * rows), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Monaco.ttf", 11)
    except Exception:
        font = ImageFont.load_default()

    for i, (key, count) in enumerate(take):
        col = i % cols
        row = i // cols
        x0 = col * cell_w
        y0 = row * cell_h
        page, idx = key.split(",")
        page = int(page[1:])
        idx = int(idx)
        glyph_img = render_glyph(rom, page, idx, scale=args.scale)
        sheet.paste(glyph_img, (x0 + 4, y0 + 4))
        label = f"{key} ×{count}"
        draw.text((x0 + 4, y0 + cell_h - 16), label, fill="black", font=font)
        draw.rectangle((x0, y0, x0 + cell_w - 1, y0 + cell_h - 1), outline="lightgray")

    out = OUT_DIR / "unmapped.png"
    sheet.save(out)
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
