#!/usr/bin/env python3
"""Render specific ROM positions at high zoom for manual identification."""
from PIL import Image, ImageDraw, ImageFont
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

SCALE = 20
out = Path('.moneo-artifacts/font-id')
out.mkdir(parents=True, exist_ok=True)

# Render a range of chars with labels for identification
def render_range(rom_page, idx_start, count, label):
    cols = min(8, count)
    rows = (count + cols - 1) // cols
    GW = 16*SCALE + 4
    GH = 16*SCALE + 24  # extra space for idx label
    img = Image.new("RGB", (GW * cols, GH * rows), (40, 40, 40))
    draw = ImageDraw.Draw(img)
    for i in range(count):
        idx = idx_start + i
        if idx > 255: break
        row, col = i // cols, i % cols
        g = render_rom_glyph(rom_page, idx)
        g = g.resize((16*SCALE, 16*SCALE), Image.NEAREST)
        g_rgb = g.convert("RGB")
        img.paste(g_rgb, (col*GW + 2, row*GH + 2))
        draw.text((col*GW + 2, row*GH + 16*SCALE + 4), f"{idx}", fill=(200, 200, 100))
    img.save(out / f"range_p{rom_page}_{idx_start}-{idx_start+count-1}_{label}.png")
    print(f"Saved range_p{rom_page}_{idx_start}-{idx_start+count-1}_{label}.png")

# From glyph_table, the 13 missing chars map to these glyph_table positions:
# glyph_table key → suspected char → rom_to_gt key formula
# For ROM(rp, ib) → GT key = F{rp//2+1},{(rp%2)*256+ib}
# Inverse: GT F{p},{gid} → rom_page=(p-1)*2+(gid//256), idx_byte=gid%256

# Known wrong OCR entries from glyph_table:
# 상: glyph_table says F3,92 = 디 → rom_page=(3-1)*2+(92//256)=4, idx=92 → ROM(4,92)
# 선: glyph_table says F3,120 = ? → ROM(4,120)
# 좌: glyph_table says ? - need to find where 좌 is
# 직: glyph_table says ? → ROM(1,107) from tutorial hypothesis  
# 항: glyph_table says F3,227? → ROM(4,227)? need to check
# 합: ?
# 택: ?

# Let me render the key areas from glyph_table that contain the 13 chars
# 상,선: ㅅ range → probably in page 5 around idx 86-130 (as seen in grid)
# 좌: ㅈ range → probably page 5 or 6
# 직: ㅈ range
# 항,합,택: ㅎ/ㅌ range → page 6?

# Based on visible font grid, 사 was at idx≈86 in page5
# Korean order: 사(86)...상... 새...
# 상 = ㅅ+ㅏ+ㅇ: after 삿(ㅅ), before 새 group

# Let me render around idx 100-120 in page 5
render_range(5, 86, 40, "sa_group")

# Also render around ROM(4,92) which should be 상 per glyph_table
render_range(4, 88, 16, "f4_88-103_sang_area")

# Render around ROM(4,120) which should be 선
render_range(4, 116, 16, "f4_116-131_sun_area")

# For ㅈ chars (좌,직): after ㅅ/ㅆ group
# 사 was at page5 idx≈86, if ㄱ-ㅅ spans about 200 chars each initial
# then ㅈ would be maybe page5 idx 180-255 or page6 start
render_range(5, 180, 64, "p5_180_jo_area")
render_range(6, 0, 64, "p6_start")

# For ㅎ (항,합): near end of all chars
render_range(6, 180, 64, "p6_180_ha_area")
