#!/usr/bin/env python3
"""Render individual chars from F4/F5 grids at high zoom for identification."""
from PIL import Image
from pathlib import Path

ROM = bytearray(Path("Pocket Monsters - LeafGreen (Korean).gba").read_bytes())
FONT_BASE = 0x780000

def render_rom_glyph(rom_page, idx_byte):
    off = FONT_BASE + rom_page * 0x2000 + idx_byte * 32
    img = Image.new("L", (16, 16), 0)
    p = img.load()
    BRIGHTNESS = [0, 80, 160, 255]
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

SCALE = 16
out = Path('.moneo-artifacts/font-id')
out.mkdir(parents=True, exist_ok=True)

def render_grid_section(rom_page, idx_start, count=64, cols=8, label=""):
    """Render a section of the font grid."""
    rows = (count + cols - 1) // cols
    GW = 16 * SCALE + 2
    img = Image.new("L", (GW * cols, GW * rows), 128)  # grey background
    for i in range(count):
        idx = idx_start + i
        if idx > 255: break
        row, col = i // cols, i % cols
        g = render_rom_glyph(rom_page, idx)
        g = g.resize((16*SCALE, 16*SCALE), Image.NEAREST)
        img.paste(g, (col * GW, row * GW))
    img.save(out / f"page{rom_page}_start{idx_start}_{label}.png")
    print(f"Saved page{rom_page}_start{idx_start}_{label}.png")

# The tutorial "상하좌우로 움직이거나 항목을 선택합니다。"
# 상 has ㅅ initial + ㅏ vowel + ㅇ final
# Looking at F4 grid: ㅁ group is at start, then goes through ㅂ then ㅅ
# ㅅ group: 사산살삼삽삿상새 etc.
# If ㅁ chars are at idx 0-80ish and ㅂ chars 80-160ish, then ㅅ chars would be 160-200ish

# F4 contains chars in range ???. Let me render sections:
render_grid_section(4, 128, 64, 8, "mid1")
render_grid_section(4, 192, 64, 8, "mid2") 

# Also render F5 section (rom_page=5) which has more ㅅ/ㅈ/ㅎ chars
render_grid_section(5, 0, 64, 8, "start")
render_grid_section(5, 64, 64, 8, "mid")

# Also F6 (rom_page=6) 
render_grid_section(6, 0, 64, 8, "start")

# Also: what about the chars in the tutorial that are clearly from pages 1-3?
# 하(1,178), 거(1,168), 나(1,91), 을(1,70), 이(1,98) - let me render around those known positions
render_grid_section(1, 155, 32, 8, "around_ha")  # 하 at idx=178
render_grid_section(1, 60, 32, 8, "around_g1")   # check 거/기 area

# Also render the full F2 range where many tutorial chars might be
render_grid_section(2, 160, 64, 8, "mid_f2")
render_grid_section(2, 0, 64, 8, "start_f2")
