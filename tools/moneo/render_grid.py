#!/usr/bin/env python3
"""Find and render records that look like the tutorial text using systematic search."""
from PIL import Image
import json
from pathlib import Path

ROM = bytearray(Path("Pocket Monsters - LeafGreen (Korean).gba").read_bytes())
FONT_BASE = 0x780000
BRIGHTNESS = [0, 80, 160, 255]

def render_glyph(rom_page, idx_byte):
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
                        if v: p[col_half*8 + half*4 + px, row_half*8 + row] = BRIGHTNESS[v]
    return img

raw = json.load(open('.moneo-artifacts/rom-text-ko-raw.json'))

# Print what record 80 contains
rec80 = next((r for r in raw['records'] if r.get('id') == 80), None)
if rec80:
    bs = bytes.fromhex(rec80['hex'])
    toks = []
    i = 0
    while i < len(bs):
        b = bs[i]
        if b == 0xFF: break
        if 0xF1 <= b <= 0xF6 and i+1 < len(bs):
            toks.append((b-0xF0, bs[i+1]))
            i += 2
        elif b in (0xFC, 0xFD) and i+1 < len(bs): i += 2
        else: i += 1
    print(f"Record 80: {toks}")
    print(f"Hex: {rec80['hex']}")

# Render known correct chars for reference
SCALE = 6
out = Path('.moneo-artifacts/reference-glyphs')
out.mkdir(parents=True, exist_ok=True)

# Definitely correct chars (visually confirmed or glyph_table reliable)
reference = [
    ('하', 1, 178),
    ('가', 1, 102),
    ('나', 1, 91),
    ('다', 2, 40),
    ('로', 2, 38),   # glyph_table says '로'
    ('이', 1, 98),   # glyph_table says '이'
]

for ch, p, idx in reference:
    g = render_glyph(p, idx)
    g.resize((16*SCALE, 16*SCALE), Image.NEAREST).save(out / f"REF_{ch}_{p}_{idx}.png")

# The key question: what chars look like in this font
# Let me render the full F1 second half (gids 256-511, accessed via 0xF1)
# in a grid to identify the font's character sequence
GRID_COLS = 16
GRID_ROWS = 16  # 256 chars per page
GLYPH_SIZE = 16
SCALE = 3

# F1 second half: rom_page=1, idx=0..255
grid_img = Image.new("L", (GRID_COLS * GLYPH_SIZE * SCALE, GRID_ROWS * GLYPH_SIZE * SCALE), 0)
for idx in range(256):
    row = idx // GRID_COLS
    col = idx % GRID_COLS
    g = render_glyph(1, idx).resize((GLYPH_SIZE*SCALE, GLYPH_SIZE*SCALE), Image.NEAREST)
    grid_img.paste(g, (col * GLYPH_SIZE * SCALE, row * GLYPH_SIZE * SCALE))

grid_img.save(out / "F1_second_half_grid.png")
print(f"Saved F1_second_half_grid.png (rom page 1, idx 0..255)")

# Also render F4 (rom_page=4)
grid_img2 = Image.new("L", (GRID_COLS * GLYPH_SIZE * SCALE, GRID_ROWS * GLYPH_SIZE * SCALE), 0)
for idx in range(256):
    row = idx // GRID_COLS
    col = idx % GRID_COLS
    g = render_glyph(4, idx).resize((GLYPH_SIZE*SCALE, GLYPH_SIZE*SCALE), Image.NEAREST)
    grid_img2.paste(g, (col * GLYPH_SIZE * SCALE, row * GLYPH_SIZE * SCALE))

grid_img2.save(out / "F4_grid.png")
print(f"Saved F4_grid.png (rom page 4, idx 0..255)")
