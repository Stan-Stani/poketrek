#!/usr/bin/env python3
"""Render all tokens from the tutorial record for identification."""
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

SCALE = 32
out = Path('.moneo-artifacts/font-id/tutorial')
out.mkdir(parents=True, exist_ok=True)

tutorial_tokens = [
    (244, 198), (241, 178), (241, 158), (241, 219), (242, 177),
    (241, 108), (241, 107), (241, 26),  (241, 168), (242, 174), (243, 195),
]
expected = ['상?','하✓','좌?','우?','로?','움?','직?','이?','거?','나?','。?']

for i, (pb, ib) in enumerate(tutorial_tokens):
    P = pb - 0xF0
    g = render_rom_glyph(P, ib).resize((16*SCALE, 16*SCALE), Image.NEAREST)
    single = Image.new("RGB", (16*SCALE, 16*SCALE + 50), (30, 30, 30))
    single.paste(g.convert("RGB"), (0, 0))
    draw = ImageDraw.Draw(single)
    draw.text((4, 16*SCALE + 5), f"P{P},{ib} pos{i+1} {expected[i]}", fill=(255,255,100))
    single.save(out / f"pos{i+1:02d}_P{P}_{ib}.png")

print("Done")
