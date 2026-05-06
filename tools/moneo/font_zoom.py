#!/usr/bin/env python3
"""Read the font grid visually by zooming into specific rows to identify chars.

Strategy: render the F1 grid at high resolution and zoom into idx=90..115 range
to confirm the chars around 가 (idx=102) and identify neighbors.
This gives us the local ordering of the font near known positions.
"""
from PIL import Image
from pathlib import Path

ROM = bytearray(Path("Pocket Monsters - LeafGreen (Korean).gba").read_bytes())
FONT_BASE = 0x780000
BRIGHTNESS = [0, 80, 160, 255]

def render_rom_glyph(rom_page, idx_byte, scale=12):
    off = FONT_BASE + rom_page * 0x2000 + idx_byte * 32
    # Render at 16x16 first then scale
    img16 = Image.new("L", (16, 16), 0)
    p = img16.load()
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
    if scale == 1:
        return img16
    return img16.resize((16*scale, 16*scale), Image.NEAREST)

out = Path('.moneo-artifacts/font-zoom')
out.mkdir(parents=True, exist_ok=True)

SCALE = 10

def render_strip(rom_page, idx_start, idx_end, label=""):
    n = idx_end - idx_start
    W = 16 * SCALE
    strip = Image.new("L", (W * n, 16 * SCALE), 0)
    for i, idx in enumerate(range(idx_start, idx_end)):
        g = render_rom_glyph(rom_page, idx, scale=1)
        g = g.resize((W, 16*SCALE), Image.NEAREST)
        strip.paste(g, (i * W, 0))
    fname = f"page{rom_page}_idx{idx_start}-{idx_end}{label}.png"
    strip.save(out / fname)
    print(f"Saved {fname}")
    return out / fname

# Render around 가 (rom_page=1, idx=102) to confirm and identify neighbors
render_strip(1, 94, 118, "_around_ga")  # 가 should be at 102 (col 8 of strip)

# Render around 하 (rom_page=1, idx=178) to confirm and identify neighbors
render_strip(1, 170, 194, "_around_ha")  # 하 should be at 178 (col 8 of strip)

# Render the key missing chars' suspected positions
# ROM(4,198) = 상 suspect - let's look at F4 idx=190-210
render_strip(4, 190, 214, "_around_sang")

# ROM(1,3) = ? (appears before 하 many times)
render_strip(1, 0, 24, "_f1_start")

# Render F3 (rom_page=3) idx=0-32 to see what's there
render_strip(3, 0, 24, "_f3_start")

# The tutorial chars based on suspected positions:
tut_positions = [(4,198,'상'),(1,158,'좌'),(1,219,'우'),(2,177,'로'),(1,108,'움'),
                 (1,107,'직'),(1,26,'이'),(1,168,'거'),(2,174,'나'),(3,195,'?')]
print("\nRendering tutorial suspect positions as individuals:")
SCALE2 = 16
for p, idx, exp in tut_positions:
    g = render_rom_glyph(p, idx, scale=SCALE2)
    fname = f"suspect_{p}_{idx}_exp{exp}.png"
    g.save(out / fname)
    print(f"  Saved {fname}")
