#!/usr/bin/env python3
"""Render random records from the corpus as image strips to find recognizable Korean."""
from PIL import Image
import json, random
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

def record_to_tokens(hex_str):
    bs = bytes.fromhex(hex_str)
    toks = []
    i = 0
    while i < len(bs):
        b = bs[i]
        if b == 0xFF: break
        if 0xF1 <= b <= 0xF6 and i+1 < len(bs):
            toks.append((b-0xF0, bs[i+1]))
            i += 2
        elif b == 0xFE:
            toks.append(('NL', 0))
            i += 1
        elif b in (0xFA, 0xFB):
            toks.append(('BRK', 0))
            i += 1
        elif b in (0xFC, 0xFD) and i+1 < len(bs): i += 2
        else: i += 1
    return toks

raw = json.load(open('.moneo-artifacts/rom-text-ko-raw.json'))
SCALE = 4
out = Path('.moneo-artifacts/record-strips')
out.mkdir(parents=True, exist_ok=True)

# Sample records of various lengths
samples = [r for r in raw['records'] if len(r['hex'])//2 >= 12][:100]

for rec in samples[:100]:
    toks = [t for t in record_to_tokens(rec['hex']) if t[0] != 'NL' and t[0] != 'BRK']
    if len(toks) < 4: continue
    
    glyphs = []
    for (p, idx) in toks:
        g = render_glyph(p, idx).resize((16*SCALE, 16*SCALE), Image.NEAREST)
        glyphs.append(g)
    
    n = len(glyphs)
    strip = Image.new("L", (16*SCALE*n, 16*SCALE), 0)
    for i, g in enumerate(glyphs):
        strip.paste(g, (i*16*SCALE, 0))
    
    rec_id = rec.get('id', raw['records'].index(rec))
    strip.save(out / f"rec_{rec_id:04d}_{n}chars.png")

print(f"Saved {len(samples)} record strips to {out}/")
