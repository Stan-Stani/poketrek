#!/usr/bin/env python3
"""
Render all 768 Korean font glyphs from the Korean LeafGreen ROM.

Font format: GBA 4bpp tiled, 16x16 px, 4 tiles of 8x8, 128 bytes/glyph.
6 pages x 128 glyphs = 768 total, at ROM 0x780000-0x798000.

Usage:
    python3 tools/render_korean_font.py [rom_path] [output_dir]

Defaults:
    rom_path   = "Pocket Monsters - LeafGreen (Korean).gba"
    output_dir = ".moneo-artifacts/font-glyphs"

Outputs:
    - font_all_pages.png   -- full contact sheet, all 768 glyphs
    - font_page_N.png      -- per-page contact sheets (pages 1-6)
    - individual/PPPP_II.png -- individual glyph images (page_index)
"""
import os
import sys
import struct

try:
    from PIL import Image
except ImportError:
    print("Requires Pillow: pip install Pillow", file=sys.stderr)
    sys.exit(1)

# Font layout constants from reverse engineering
FONT_BASE = 0x780000          # ROM offset of first Korean font page
FONT_PTR_TABLE = 0x38492C     # Font pointer table (17 entries)
PAGES = 6                     # Korean font pages (F1-F6)
GLYPHS_PER_PAGE = 128
PAGE_SIZE = 0x4000            # 16384 bytes = 128 x 128
GLYPH_BYTES = 128             # 4 tiles x 32 bytes
TILE_BYTES = 32               # 8x8 pixels at 4bpp
GLYPH_PX = 16                 # 16x16 pixel glyphs
SCALE = 4                     # Upscale factor for readability


def render_glyph(rom, offset):
    """Render a single 16x16 glyph from 4bpp tiled data."""
    img = Image.new('L', (GLYPH_PX, GLYPH_PX), 0)
    for tile_idx in range(4):
        tx = (tile_idx % 2) * 8
        ty = (tile_idx // 2) * 8
        for row in range(8):
            for px in range(4):
                byte = rom[offset + tile_idx * TILE_BYTES + row * 4 + px]
                p0 = byte & 0x0F
                p1 = (byte >> 4) & 0x0F
                if p0:
                    img.putpixel((tx + px * 2, ty + row), p0 * 17)
                if p1:
                    img.putpixel((tx + px * 2 + 1, ty + row), p1 * 17)
    return img


def render_contact_sheet(rom, base, count, cols=16):
    """Render a grid of glyphs as a contact sheet."""
    rows = (count + cols - 1) // cols
    cell = GLYPH_PX + 1  # 1px gap
    img = Image.new('L', (cols * cell, rows * cell), 0)
    for g in range(count):
        glyph = render_glyph(rom, base + g * GLYPH_BYTES)
        gx = (g % cols) * cell
        gy = (g // cols) * cell
        img.paste(glyph, (gx, gy))
    # Scale up for readability
    return img.resize((img.width * SCALE, img.height * SCALE), Image.NEAREST)


def main():
    rom_path = sys.argv[1] if len(sys.argv) > 1 else \
        "Pocket Monsters - LeafGreen (Korean).gba"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else \
        ".moneo-artifacts/font-glyphs"

    if not os.path.exists(rom_path):
        print("ROM not found: {}".format(rom_path), file=sys.stderr)
        sys.exit(1)

    with open(rom_path, 'rb') as f:
        rom = f.read()

    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(out_dir, "individual"), exist_ok=True)

    print("ROM: {} ({:,} bytes)".format(rom_path, len(rom)))
    print("Font base: 0x{:06X}, {} pages x {} glyphs".format(
        FONT_BASE, PAGES, GLYPHS_PER_PAGE))

    # Verify font pointer table
    print("\nFont pointer table at 0x{:06X}:".format(FONT_PTR_TABLE))
    for i in range(min(17, (len(rom) - FONT_PTR_TABLE) // 4)):
        ptr = struct.unpack_from('<I', rom, FONT_PTR_TABLE + i * 4)[0]
        suffix = ""
        if 1 <= i <= 6:
            rom_off = ptr & 0x01FFFFFF
            suffix = "  -> ROM 0x{:06X}  (Korean page {})".format(rom_off, i)
        print("  [{:2d}] = 0x{:08X}{}".format(i, ptr, suffix))

    # Render per-page contact sheets
    for page in range(PAGES):
        page_num = page + 1  # F1-F6
        base = FONT_BASE + page * PAGE_SIZE
        sheet = render_contact_sheet(rom, base, GLYPHS_PER_PAGE)
        path = os.path.join(out_dir, "font_page_{}.png".format(page_num))
        sheet.save(path)
        print("Saved {} (page F{}, {} glyphs)".format(
            path, page_num, GLYPHS_PER_PAGE))

    # Render full contact sheet (all pages)
    full = render_contact_sheet(rom, FONT_BASE,
                                PAGES * GLYPHS_PER_PAGE, cols=16)
    full_path = os.path.join(out_dir, "font_all_pages.png")
    full.save(full_path)
    print("Saved {} (all {} glyphs)".format(
        full_path, PAGES * GLYPHS_PER_PAGE))

    # Render individual glyphs
    for page in range(PAGES):
        for idx in range(GLYPHS_PER_PAGE):
            offset = FONT_BASE + page * PAGE_SIZE + idx * GLYPH_BYTES
            glyph = render_glyph(rom, offset)
            glyph_big = glyph.resize((GLYPH_PX * SCALE, GLYPH_PX * SCALE),
                                     Image.NEAREST)
            path = os.path.join(out_dir, "individual",
                                "F{}_{:03d}.png".format(page + 1, idx))
            glyph_big.save(path)

    print("Saved {} individual glyphs to {}/individual/".format(
        PAGES * GLYPHS_PER_PAGE, out_dir))

    # Count non-blank glyphs
    blank = 0
    for g in range(PAGES * GLYPHS_PER_PAGE):
        offset = FONT_BASE + g * GLYPH_BYTES
        chunk = rom[offset:offset + GLYPH_BYTES]
        if all(b == 0 for b in chunk):
            blank += 1
    print("\nNon-blank glyphs: {} / {}".format(
        PAGES * GLYPHS_PER_PAGE - blank, PAGES * GLYPHS_PER_PAGE))
    print("Blank glyphs: {}".format(blank))


if __name__ == '__main__':
    main()
