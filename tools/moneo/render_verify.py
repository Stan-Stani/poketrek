#!/usr/bin/env python3
"""Render ROM font glyphs at specific positions to verify chars."""
from PIL import Image
import json
from pathlib import Path

ROM_PATH = "Pocket Monsters - LeafGreen (Korean).gba"
FONT_BASE = 0x780000
SCALE = 8  # scale for visibility

def read_glyph_16x16(off):
    """Read 16×16 glyph at ROM file offset `off`.
    ROM stores 2bpp data. Layout: top-left 8×8 (16 bytes), top-right 8×8 (16 bytes),
    then bottom-left at off+256, bottom-right at off+272.
    Actually for render_dialogue_v8 style: 16×8 at off (32 bytes).
    For full 16×16: need second 16×8 at off+0x100 (256 bytes later).
    """
    img = Image.new("L", (16*SCALE, 16*SCALE), 0)
    p = img.load()
    rom = Path(ROM_PATH).read_bytes()
    
    BRIGHTNESS = [0, 80, 160, 255]
    
    for row_half in range(2):
        base = off + row_half * 0x100  # top half at off, bottom half at off+256
        for col_half in range(2):
            tile_off = base + col_half * 0x10  # left=+0, right=+16
            for row in range(8):
                byte_off = tile_off + row * 2
                if byte_off + 1 >= len(rom):
                    continue
                for half in range(2):
                    b = rom[byte_off + (1 - half)]
                    for px in range(4):
                        v = (b >> ((3 - px) * 2)) & 0x3
                        x = col_half * 8 + half * 4 + px
                        y = row_half * 8 + row
                        c = BRIGHTNESS[v]
                        for sy in range(SCALE):
                            for sx in range(SCALE):
                                p[x*SCALE + sx, y*SCALE + sy] = c
    return img

def glyph_offset(rom_page, idx_byte):
    """ROM file offset for glyph at (rom_page, idx_byte)."""
    return FONT_BASE + rom_page * 0x2000 + idx_byte * 32

def main():
    # Verified chars from ko_charmap (ground truth)
    # ROM positions derived from formula: gt_key = F{rom_page//2+1},{(rom_page%2)*256+idx}
    # With known mappings from glyph_table:
    verify = {
        '하': (1, 178),   # glyph_table F1,434 = 하 ✓
        '거': (1, 47-256+256, ),  # hmm let me recalc
    }
    
    # From ko_charmap chars and my new_map:
    # new_map has ROM positions. Let me extract them from glyph-map.json
    gm = json.load(open('tools/moneo/glyph-map.json'))
    new_map = gm['map']
    
    # Find positions for known chars
    ko = json.load(open('app/src/main/assets/moneo/ko_charmap.json'))
    ko_chars = set(ko.values())
    
    missing_in_map = ['상', '선', '좌', '직', '택', '항', '합', '아', '용', '움', '정', '계']
    
    # For chars that ARE in glyph_table, show their ROM images
    found_in_map = {}
    for key, ch in new_map.items():
        if ch in missing_in_map and key not in found_in_map:
            found_in_map[ch] = key
    
    print("Chars found in new_map:", sorted(found_in_map.keys()))
    
    # Render chars that are possibly wrong (OCR errors in glyph_table at F3,88-96)
    # These positions: ROM(page=4, idx=88..96)
    out = Path('.moneo-artifacts/verify-glyphs')
    out.mkdir(parents=True, exist_ok=True)
    
    # Chars to verify from tutorial: known and suspected positions
    to_render = [
        # (rom_page, idx_byte, expected_char)
        (1, 178, '하'),     # F1,434 confirmed
        (4, 92, '상?'),     # F3,92 - glyph_table says '디', ksx1001 says '상'  
        (4, 120, '선?'),    # F3,120 - ksx1001 says '선'
        (5, 73, '아?'),     # F3,329 = F{3//2+1=2},{(3%2)*256+73=329} -> F2,329... hmm
    ]
    
    # Actually recalc: which ROM page,idx maps to ksx1001 positions?
    # ksx1001 is in its own coord system, not rom font coords
    # So just render ROM positions my formula gives for missing chars
    
    # All chars in new_map that should be checked
    check_chars = list(missing_in_map) + ['하', '가', '나', '다', '로', '를']
    
    for ch in check_chars:
        positions = [k for k, v in new_map.items() if v == ch]
        if positions:
            # Render first position
            key = positions[0]
            parts = key.split(',')
            rom_page = int(parts[0][1:])  # "F1" -> 1
            idx_byte = int(parts[1])
            off = glyph_offset(rom_page, idx_byte)
            print(f"  Rendering {ch!r} at ROM({rom_page},{idx_byte}) off={off:#x}")
            img = read_glyph_16x16(off)
            img.save(out / f"char_{ch}_{key.replace(',','_')}.png")
        else:
            print(f"  {ch!r}: NOT IN new_map")
    
    # Also render suspicious F3,88-96 range 
    print("\nRendering glyph_table F3 range gids 88..96:")
    for gid in range(88, 97):
        # F3,gid -> ROM(page=4, idx=gid) for gid<256
        off = glyph_offset(4, gid)
        img = read_glyph_16x16(off)
        gt_char = json.load(open('.moneo-artifacts/glyph-table.json')).get(f'F3,{gid}', '?')
        img.save(out / f"F3_{gid:03d}_gt={gt_char}.png")
        print(f"  F3,{gid}: gt={gt_char!r}")
    
    print(f"\nImages written to {out}/")

if __name__ == '__main__':
    main()
