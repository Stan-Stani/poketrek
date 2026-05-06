#!/usr/bin/env python3
"""
Render all Korean font glyphs from the Korean LeafGreen ROM.

Font format: GBA-native packed 2bpp, 16x16 px,
stored in pokefirered grid layout (NOT contiguous).
6 pages x 512 glyphs = 3072 total, at ROM 0x780000-0x798000.

Usage:
    python3 tools/render_korean_font.py [rom_path] [output_dir]

Defaults:
    rom_path   = "Pocket Monsters - LeafGreen (Korean).gba"
    output_dir = ".moneo-artifacts/font-glyphs"

Outputs:
    - font_all_pages.png   -- full contact sheet, all 3072 glyphs
    - font_page_N.png      -- per-page contact sheets (pages 1-6)
    - individual/PPPP_III.png -- individual glyph images (page_index)
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
GLYPHS_PER_PAGE = 512         # Grid: 32 rows x 16 cols
GLYPHS_PER_ROW = 16           # Glyphs per grid row
PAGE_SIZE = 0x4000             # 16384 bytes per page
GLYPH_PX = 16                 # 16x16 pixel glyphs
SCALE = 4                     # Upscale factor for readability

# 2bpp brightness map: palette index -> grayscale
BRIGHTNESS = [0, 255, 180, 100]


def glyph_byte_offset(glyph_id):
    """Compute byte offset of a glyph within its page (pokefirered grid layout)."""
    row = glyph_id // GLYPHS_PER_ROW
    col = glyph_id % GLYPHS_PER_ROW
    return 0x200 * row + 0x20 * col


def render_glyph(rom, page_base, glyph_id):
    """Render a single 16x16 glyph from packed 2bpp data.

    Format: each byte holds 4 pixels (2 bits each).
    Within each 8-pixel row of an 8x8 sub-tile:
      - byte at offset+1 holds the LEFT 4 pixels
      - byte at offset+0 holds the RIGHT 4 pixels
      - Within each byte, the HIGH 2 bits are the LEFTMOST pixel
    Each 8x8 sub-tile is 16 bytes (8 rows x 2 bytes/row).
    Sub-tile order within glyph: TL=+0, TR=+16, BL=+256, BR=+272.
    """
    img = Image.new('L', (GLYPH_PX, GLYPH_PX), 0)
    off = page_base + glyph_byte_offset(glyph_id)
    for dx, dy, tile_off in [(0, 0, 0), (8, 0, 16), (0, 8, 256), (8, 8, 272)]:
        for row in range(8):
            # Byte order swapped: byte 1 = left half, byte 0 = right half
            for half in range(2):
                byte_idx = 1 - half  # half=0 reads byte 1 (left); half=1 reads byte 0 (right)
                b = rom[off + tile_off + row * 2 + byte_idx]
                for px in range(4):
                    # High bits = leftmost pixel within byte
                    v = (b >> ((3 - px) * 2)) & 0x3
                    if v > 0:
                        img.putpixel((dx + half * 4 + px, dy + row),
                                     BRIGHTNESS[v])
    return img


def is_blank(rom, page_base, glyph_id):
    """Check if a glyph slot contains all zeros."""
    off = page_base + glyph_byte_offset(glyph_id)
    for tile_off in [0, 16, 256, 272]:
        for i in range(16):
            if rom[off + tile_off + i] != 0:
                return False
    return True


def render_contact_sheet(rom, page_base, count, cols=16):
    """Render a grid of glyphs as a contact sheet."""
    rows = (count + cols - 1) // cols
    cell = GLYPH_PX + 1  # 1px gap
    img = Image.new('L', (cols * cell, rows * cell), 0)
    for g in range(count):
        glyph = render_glyph(rom, page_base, g)
        gx = (g % cols) * cell
        gy = (g // cols) * cell
        img.paste(glyph, (gx, gy))
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
    print("Font: 2bpp grid, 0x{:06X}, {} pages x {} glyphs".format(
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

    # Render per-page contact sheets and count glyphs
    total_non_blank = 0
    for page in range(PAGES):
        page_num = page + 1  # F1-F6
        base = FONT_BASE + page * PAGE_SIZE
        non_blank = sum(1 for g in range(GLYPHS_PER_PAGE)
                        if not is_blank(rom, base, g))
        total_non_blank += non_blank

        sheet = render_contact_sheet(rom, base, GLYPHS_PER_PAGE)
        path = os.path.join(out_dir, "font_page_{}.png".format(page_num))
        sheet.save(path)
        print("Saved {} (page F{}, {}/{} non-blank)".format(
            path, page_num, non_blank, GLYPHS_PER_PAGE))

    # Render individual glyphs
    for page in range(PAGES):
        base = FONT_BASE + page * PAGE_SIZE
        for idx in range(GLYPHS_PER_PAGE):
            if is_blank(rom, base, idx):
                continue
            glyph = render_glyph(rom, base, idx)
            glyph_big = glyph.resize((GLYPH_PX * SCALE, GLYPH_PX * SCALE),
                                     Image.NEAREST)
            path = os.path.join(out_dir, "individual",
                                "F{}_{:03d}.png".format(page + 1, idx))
            glyph_big.save(path)

    print("Saved individual glyphs to {}/individual/".format(out_dir))
    print("\nTotal non-blank: {} / {}".format(
        total_non_blank, PAGES * GLYPHS_PER_PAGE))


if __name__ == '__main__':
    main()
