#!/usr/bin/env python3
"""Render glyphs from the discovered patched-font atlases using the EXACT
encoding extracted from the runtime decoder at 0x08002fa0.

Encoding:
- Source: 2 bits per pixel, MSB-first within each byte.
  * pixel 0 (leftmost) = bits 6-7
  * pixel 1            = bits 4-5
  * pixel 2            = bits 2-3
  * pixel 3 (rightmost)= bits 0-1
- Source bytes are stored as 16-bit big-endian halfwords (the decoder
  reads byte[+1] before byte[+0] for each halfword), so each halfword
  represents 8 horizontally-adjacent pixels.
- Color remap (verified against the runtime ROM LUT @ 0x081ea090 and
  IWRAM LUT @ 0x03000a40):
      raw 2bpp 0  -> 4bpp 0  (transparent / paper)
      raw 2bpp 1  -> 4bpp 2  (layer-A jamo color)
      raw 2bpp 2  -> 4bpp 3  (layer-B jamo color)
      raw 2bpp 3  -> 4bpp 0  (unused / treated as transparent)

Atlas layouts (per handler call patterns at 0x800645c..0x800696c):
- Atlas 0 (font_base 0x08edf800): handler 0 makes 2 decoder calls
  consuming 32 source bytes => 128 pixels per glyph. Empirically a
  16x8 hangul half-cell (e.g., initial-consonant or syllable lower).
- Atlas 1 (font_base 0x08f18800): handler 1 makes 4 calls consuming
  64 source bytes => 256 pixels => 16x16.
- Atlas 2 (font_base 0x08f51800): same shape as atlas 1 (16x16).
"""
from __future__ import annotations
import argparse
from pathlib import Path
from PIL import Image

ROM = Path(__file__).resolve().parent / "leafgreen_J-K_2024.gba"
GBA_BASE = 0x08000000

ATLASES = [
    # label, font_base, width_base, source_bytes_per_glyph, width, height
    ("atlas0", 0x08edf800, 0x08f17800, 32, 16, 8),
    ("atlas1", 0x08f18800, 0x08f50800, 64, 16, 16),
    ("atlas2", 0x08f51800, 0x08f89800, 64, 16, 16),
]

PALETTE = {0: 0, 1: 0, 2: 128, 3: 255}


def decode_2bpp_tile_8x8(src: bytes, off: int) -> list[list[int]]:
    """Decode 16 bytes at src[off..off+16] as one 8x8 2bpp tile.

    Per the decoder (0x08002fa0), bytes are read in big-endian-halfword
    order: byte[+1] before byte[+0]. So for each row (2 bytes), the
    +1 byte (high byte of the BE halfword) holds the LEFT 4 pixels and
    the +0 byte holds the RIGHT 4 pixels.

    Within each byte the pixels are MSB-first (pixel 0 = bits 6-7).

    Returns 8 rows × 8 cols of 2bpp values (0..3).
    """
    rows = []
    for r in range(8):
        b_lo = src[off + r * 2 + 0]   # right 4 pixels (decoder reads 2nd)
        b_hi = src[off + r * 2 + 1]   # left  4 pixels (decoder reads 1st)
        row = []
        for b in (b_hi, b_lo):
            for px in range(4):
                v = (b >> ((3 - px) * 2)) & 0x3
                row.append(v)
        rows.append(row)
    return rows


def remap_2bpp_to_grayscale(v: int) -> int:
    # ROM/IWRAM LUT remap: raw 2bpp -> 4bpp
    # 0 -> 0, 1 -> 2, 2 -> 3, 3 -> 0
    return PALETTE[{0: 0, 1: 2, 2: 3, 3: 0}[v]]


def decode_glyph(src: bytes, width: int, height: int) -> Image.Image:
    """Each 16-source-byte chunk is one 8x8 2bpp tile.

    Atlas 0 (handler 0, 32 src bytes, shape 16x8): 2 tiles laid out
    side-by-side as a 16x8 strip (left tile + right tile).

    Atlas 1/2 (handler 1, 64 src bytes, shape 16x16): 4 tiles in
    GBA-typical reading order — top-left, top-right, bottom-left,
    bottom-right.
    """
    im = Image.new("L", (width, height), 0)
    pixels = im.load()
    if len(src) == 32 and (width, height) == (16, 8):
        tile_offsets = [(0, 0), (8, 0)]
    elif len(src) == 64 and (width, height) == (16, 16):
        tile_offsets = [(0, 0), (8, 0), (0, 8), (8, 8)]
    else:
        raise ValueError(f"unexpected src/shape: {len(src)} {width}x{height}")
    for tile_idx, (tx, ty) in enumerate(tile_offsets):
        tile = decode_2bpp_tile_8x8(src, tile_idx * 16)
        for r in range(8):
            for c in range(8):
                pixels[tx + c, ty + r] = remap_2bpp_to_grayscale(tile[r][c])
    return im


def render_atlas(rom: bytes, label: str, font_base: int,
                 width_base: int, src_per_glyph: int,
                 width: int, height: int,
                 n: int, start: int, out_dir: Path) -> Path:
    cols = 16
    rows = (n + cols - 1) // cols
    sheet = Image.new("L", (cols * (width + 1), rows * (height + 1)), 0)
    width_off = width_base - GBA_BASE
    widths = list(rom[width_off + start:width_off + start + n])
    print(f"{label}: font_base={font_base:08x} stride=64 src_bytes/glyph={src_per_glyph}"
          f" shape={width}x{height}")
    print(f"  widths[{start}..+16]: {widths[:16]}")
    for i in range(n):
        cp = start + i
        off = (font_base - GBA_BASE) + cp * 64
        if off + src_per_glyph > len(rom):
            break
        src = rom[off:off + src_per_glyph]
        glyph = decode_glyph(src, width, height)
        sheet.paste(glyph,
                    ((i % cols) * (width + 1), (i // cols) * (height + 1)))
    path = out_dir / f"{label}_n{n}_s{start}_decoded.png"
    sheet.save(path)
    print(f"  wrote {path}")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=256)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--out", default="/tmp/poketrek_trace/atlas_render")
    ap.add_argument("--only", choices=["atlas0", "atlas1", "atlas2"],
                    default=None)
    args = ap.parse_args()

    rom = ROM.read_bytes()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for label, font_base, width_base, src_per_glyph, w, h in ATLASES:
        if args.only and label != args.only:
            continue
        render_atlas(rom, label, font_base, width_base, src_per_glyph,
                     w, h, args.n, args.start, out_dir)


if __name__ == "__main__":
    main()
