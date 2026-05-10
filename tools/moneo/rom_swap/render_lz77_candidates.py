#!/usr/bin/env python3
"""Render the top LZ77-block candidates as PNG sprite sheets.

Decompress each candidate, interpret the bytes as 4bpp 8x8 tiles, lay them
out in a sheet (16 cols × N rows), and save as PNG so we can eyeball
whether the data is hangul glyphs.

Two layouts:
- 8x8 tile grid (raw)
- 16x16 glyph grid (bundle 4 tiles per glyph: TL, TR, BL, BR)
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("pip install Pillow", file=sys.stderr); sys.exit(1)

ROM = Path(__file__).resolve().parent / "leafgreen_J-K_2024.gba"
OUT_DIR = Path(__file__).resolve().parent / "lz77_renders"
GBA_BASE = 0x08000000

# Greyscale palette for 4bpp (0..15 → 0..255)
PALETTE = [(i * 17, i * 17, i * 17) for i in range(16)]


def lz77_decompress(data: bytes, offset: int) -> bytes | None:
    if offset + 4 > len(data) or data[offset] != 0x10:
        return None
    size = data[offset + 1] | (data[offset + 2] << 8) | (data[offset + 3] << 16)
    if size == 0 or size > 0x80000:
        return None
    src = offset + 4
    out = bytearray()
    try:
        while len(out) < size:
            if src >= len(data): return None
            flags = data[src]; src += 1
            for bit in range(8):
                if len(out) >= size: break
                if (flags & (0x80 >> bit)) == 0:
                    out.append(data[src]); src += 1
                else:
                    if src + 1 >= len(data): return None
                    hi = data[src]; lo = data[src + 1]; src += 2
                    length = (hi >> 4) + 3
                    disp = ((hi & 0x0F) << 8) | lo
                    pos = len(out) - disp - 1
                    if pos < 0: return None
                    for _ in range(length):
                        out.append(out[pos]); pos += 1
    except Exception:
        return None
    return bytes(out[:size])


def tile_to_image(tile_bytes: bytes) -> Image.Image:
    """8x8 4bpp tile → 8x8 RGB image."""
    img = Image.new("RGB", (8, 8))
    px = img.load()
    for y in range(8):
        for x in range(0, 8, 2):
            byte = tile_bytes[y * 4 + x // 2]
            lo = byte & 0xF
            hi = (byte >> 4) & 0xF
            px[x, y] = PALETTE[lo]
            px[x + 1, y] = PALETTE[hi]
    return img


def render_8x8_grid(decomp: bytes, cols: int = 16) -> Image.Image:
    n_tiles = len(decomp) // 32
    rows = (n_tiles + cols - 1) // cols
    out = Image.new("RGB", (cols * 8, rows * 8), (255, 255, 255))
    for i in range(n_tiles):
        tile = tile_to_image(decomp[i*32:(i+1)*32])
        out.paste(tile, ((i % cols) * 8, (i // cols) * 8))
    return out


def render_16x16_grid(decomp: bytes, cols: int = 16) -> Image.Image:
    """Treat 4 consecutive 8x8 tiles as a 16x16 glyph (TL TR BL BR)."""
    n_glyphs = len(decomp) // 128  # 4 tiles of 32B each
    rows = (n_glyphs + cols - 1) // cols
    out = Image.new("RGB", (cols * 16, rows * 16), (255, 255, 255))
    for i in range(n_glyphs):
        tl = tile_to_image(decomp[i*128 + 0:i*128 + 32])
        tr = tile_to_image(decomp[i*128 + 32:i*128 + 64])
        bl = tile_to_image(decomp[i*128 + 64:i*128 + 96])
        br = tile_to_image(decomp[i*128 + 96:i*128 + 128])
        gx, gy = (i % cols) * 16, (i // cols) * 16
        out.paste(tl, (gx, gy))
        out.paste(tr, (gx + 8, gy))
        out.paste(bl, (gx, gy + 8))
        out.paste(br, (gx + 8, gy + 8))
    return out


def render_2tile_glyph_grid(decomp: bytes, cols: int = 16) -> Image.Image:
    """Treat 2 consecutive 8x8 tiles as a 16x8 glyph (left/right halves)."""
    n_glyphs = len(decomp) // 64
    rows = (n_glyphs + cols - 1) // cols
    out = Image.new("RGB", (cols * 16, rows * 8), (255, 255, 255))
    for i in range(n_glyphs):
        l = tile_to_image(decomp[i*64:i*64+32])
        r = tile_to_image(decomp[i*64+32:i*64+64])
        gx, gy = (i % cols) * 16, (i // cols) * 8
        out.paste(l, (gx, gy))
        out.paste(r, (gx + 8, gy))
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", default=str(ROM))
    parser.add_argument("--gba-addrs", nargs="+", required=True,
                        help="GBA addresses (hex, 0x...) to render")
    parser.add_argument("--scale", type=int, default=4)
    args = parser.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    data = Path(args.rom).read_bytes()

    for addr_str in args.gba_addrs:
        addr = int(addr_str, 16) if addr_str.startswith("0x") else int(addr_str, 16)
        off = addr - GBA_BASE
        decomp = lz77_decompress(data, off)
        if decomp is None:
            print(f"❌ {addr:#x}: not a valid LZ77 block")
            continue
        print(f"✓ {addr:#x}: uncompressed {len(decomp)} bytes")

        # Render in three layouts
        for layout, fn in [("8x8", render_8x8_grid),
                           ("16x16", render_16x16_grid),
                           ("16x8", render_2tile_glyph_grid)]:
            img = fn(decomp)
            if args.scale != 1:
                img = img.resize((img.width * args.scale, img.height * args.scale),
                                 Image.NEAREST)
            out = OUT_DIR / f"{addr:08x}_{layout}.png"
            img.save(out)
            print(f"   → {out}  ({img.width}x{img.height})")


if __name__ == "__main__":
    main()
