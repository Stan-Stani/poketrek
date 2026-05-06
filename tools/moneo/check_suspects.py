#!/usr/bin/env python3
"""Check what ROM(1,3) and surrounding unknown chars are."""
import json
from pathlib import Path

gt = json.load(open('.moneo-artifacts/glyph-table.json'))
ks = json.load(open('.moneo-artifacts/ksx1001-charmap.json'))
gm = json.load(open('tools/moneo/glyph-map.json'))
nm = gm['map']

# Rom position (1,3) -> glyph_table F1, 256+3=F1,259
# What's in glyph_table at F1,259?
print("ROM(1,3) -> gt F1,259:", gt.get("F1,259"), "ksx F1,259:", ks.get("F1,259"))
print("ROM(1,3) in new_map:", nm.get("F1,3"))

# The tutorial suspect: ROM(4,198)=상?, ROM(1,158)=좌?, ROM(1,219)=우?, ROM(2,177)=로?
suspects = {
    'ROM(4,198)': ('상', 4, 198),
    'ROM(1,158)': ('좌', 1, 158),
    'ROM(1,219)': ('우', 1, 219),
    'ROM(2,177)': ('로', 2, 177),
    'ROM(1,108)': ('움', 1, 108),
    'ROM(1,107)': ('직', 1, 107),
    'ROM(1,26)': ('이', 1, 26),
    'ROM(1,168)': ('거', 1, 168),
    'ROM(2,174)': ('나', 2, 174),
    'ROM(3,195)': ('?', 3, 195),
}

print("\nTutorial suspects:")
for label, (expected, p, idx) in suspects.items():
    gt_key = f"F{p//2+1},{(p%2)*256+idx}"
    gt_char = gt.get(gt_key, None)
    nm_char = nm.get(f"F{p},{idx}", None)
    print(f"  {label} (expected {expected!r}): gt_key={gt_key} gt={gt_char!r} nm={nm_char!r}")

# Let's also check the ROM pixel data for key positions - render them
print("\nRendering suspect glyphs...")
from PIL import Image
ROM = bytearray(Path("Pocket Monsters - LeafGreen (Korean).gba").read_bytes())
FONT_BASE = 0x780000
SCALE = 6

def read_glyph_16x16(rom_page, idx_byte):
    off = FONT_BASE + rom_page * 0x2000 + idx_byte * 32
    img = Image.new("L", (16*SCALE, 16*SCALE), 0)
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
                        x = col_half * 8 + half * 4 + px
                        y = row_half * 8 + row
                        c = BRIGHTNESS[v]
                        for sy in range(SCALE):
                            for sx in range(SCALE):
                                p[x*SCALE+sx, y*SCALE+sy] = c
    return img

out = Path('.moneo-artifacts/tutorial-suspects')
out.mkdir(parents=True, exist_ok=True)

for label, (expected, rp, idx) in suspects.items():
    img = read_glyph_16x16(rp, idx)
    fname = f"{label.replace('ROM(','').replace(')','').replace(',','_')}_exp{expected}.png"
    img.save(out / fname)
    print(f"  Saved: {fname}")

# Also render reference chars from known positions for comparison
known = {'하': (1,178), '가': (1,102), '나': (1,91), '로': (2,38), '이': (1,98)}
for ch, (rp, idx) in known.items():
    img = read_glyph_16x16(rp, idx)
    img.save(out / f"KNOWN_{ch}_{rp}_{idx}.png")
