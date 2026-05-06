#!/usr/bin/env python3
"""Render individual chars with Korean reference text for comparison."""
from PIL import Image, ImageDraw
from pathlib import Path
import json

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

SCALE = 32
out = Path('.moneo-artifacts/font-id/singles')
out.mkdir(parents=True, exist_ok=True)

# Render a single glyph with large label
def render_single(rom_page, idx_byte, label=""):
    g = render_rom_glyph(rom_page, idx_byte)
    g = g.resize((16*SCALE, 16*SCALE), Image.NEAREST)
    img = Image.new("RGB", (16*SCALE, 16*SCALE + 50), (30, 30, 30))
    img.paste(g.convert("RGB"), (0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((4, 16*SCALE + 5), f"p{rom_page},i{idx_byte} {label}", fill=(255, 255, 100))
    fname = f"p{rom_page}_i{idx_byte}_{label}.png"
    img.save(out / fname)
    return fname

# Key chars to identify:
# From page5 range around sa group:
# 사 group: 사(no final), 삭(ㄱ), ..., 상(ㅇ), ...
# 새 group: 새(no final), 색(ㄱ), 샌(ㄴ), ...선(ㄴ)!

# If 상 is at p5,94 and 새 group starts at p5,104:
# Let's render the transition zone p5 idx 86-115
for idx in range(86, 120):
    render_single(5, idx, "")

print("Rendered p5 idx 86-119")

# Also render the ko_charmap confirmed positions for calibration:
# 가=ROM(1,102), 하=ROM(1,178), 나=ROM(1,91), 로=ROM(2,38)
render_single(1, 102, "ga_confirmed")
render_single(1, 178, "ha_confirmed")  
render_single(1, 91, "na_confirmed")
render_single(2, 38, "ro_confirmed")
print("Rendered confirmed chars for calibration")
