#!/usr/bin/env python3
"""Render a wide strip of page 5/6 to find 선/좌/직/등."""
from PIL import Image, ImageDraw
from pathlib import Path

ROM = bytearray(Path("Pocket Monsters - LeafGreen (Korean).gba").read_bytes())
FONT_BASE = 0x780000

def render_rom_glyph(rom_page, idx_byte):
    off = FONT_BASE + rom_page * 0x2000 + idx_byte * 32
    img = Image.new("L", (16, 16), 0)
    p = img.load()
    for row_half in range(2):
        base = off + row_half * 0x100
        for col_half in range(2):
            tile_off = base + col_half * 0x10
            for row in range(8):
                byte_off = tile_off + row * 2
                if byte_off + 1 >= len(ROM): continue
                for half in range(2):
                    b = ROM[byte_off + (1 - half)]
                    for px in range(4):
                        v = (b >> ((3 - px) * 2)) & 0x3
                        if v: p[col_half*8 + half*4 + px, row_half*8 + row] = 255
    return img

SCALE = 10
out = Path('.moneo-artifacts/font-id')
out.mkdir(parents=True, exist_ok=True)

def render_labeled_strip(rom_page, idx_start, count, fname):
    """Render chars with idx labels, 16 per row."""
    COLS = 16
    rows = (count + COLS - 1) // COLS
    GW = 16*SCALE + 2
    GH = 16*SCALE + 14
    img = Image.new("RGB", (GW * COLS, GH * rows), (40, 40, 40))
    draw = ImageDraw.Draw(img)
    for i in range(count):
        idx = idx_start + i
        if idx > 255: break
        row, col = i // COLS, i % COLS
        g = render_rom_glyph(rom_page, idx)
        g = g.resize((16*SCALE, 16*SCALE), Image.NEAREST)
        img.paste(g.convert("RGB"), (col*GW + 1, row*GH + 1))
        draw.text((col*GW + 1, row*GH + 16*SCALE + 2), f"{idx}", fill=(200, 200, 80), font=None)
    img.save(out / fname)
    print(f"Saved {fname}")

# Scan page 5 from 100 to 200 for 상,선,서,... 
render_labeled_strip(5, 100, 128, "p5_100-227_scan.png")

# Scan page 5 from 200 to 255 
render_labeled_strip(5, 200, 56, "p5_200-255_scan.png")

# Scan page 6 in full
render_labeled_strip(6, 0, 128, "p6_0-127_scan.png")
render_labeled_strip(6, 128, 128, "p6_128-255_scan.png")

# Also full page 2 (has 나/로 confirmed - need 아/용/움/정)
render_labeled_strip(2, 0, 128, "p2_0-127_scan.png")
render_labeled_strip(2, 128, 128, "p2_128-255_scan.png")

# Full page 3 (need 직/좌)
render_labeled_strip(3, 0, 128, "p3_0-127_scan.png")
render_labeled_strip(3, 128, 128, "p3_128-255_scan.png")

# Full page 4 
render_labeled_strip(4, 0, 128, "p4_0-127_scan.png")
render_labeled_strip(4, 128, 128, "p4_128-255_scan.png")
