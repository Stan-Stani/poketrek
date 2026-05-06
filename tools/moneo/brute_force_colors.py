#!/usr/bin/env python3
"""Brute-force the IWRAM color table using known ROM positions + ko_charmap fingerprints.

The blit converts ROM 2bpp pixels to VRAM 4bpp pixels:
  2bpp values 0,1,2,3 map to 4bpp values: 0->0, 1->c1, 2->c2, 3->0 (pixel 3 is transparent)
  table1 (256 entries) maps each ROM byte (4×2bpp pixels) to one of 81 3^4 patterns
  IWRAM[pattern] = (pix3_c<<12)|(pix2_c<<8)|(pix1_c<<4)|pix0_c
  where pix_c = 0 if pixel=0, c1 if pixel=1, c2 if pixel=2

Brute force: try c1,c2 in 0..15 × 0..15 and find which produces matching fingerprints.
"""
import struct, hashlib, json
from pathlib import Path

ROM = bytearray(Path("Pocket Monsters - LeafGreen (Korean).gba").read_bytes())
FONT_BASE = 0x780000
table1_off = 0x1CDF1C
table1 = ROM[table1_off: table1_off + 256]

# Verify the 3^4 = 81 structure of table1
# For each ROM byte, extract 4 2bpp pixels {0,1,2,3}, replace 3->0 -> 3-valued (0,1,2)
# The table1 index = ternary encoding: p0*1 + p1*3 + p2*9 + p3*27 (or some permutation)
# Let's verify:
def pixel4_to_ternary(b):
    """ROM byte -> 4 pixel values (0,1,2, treating 3 as 0) -> ternary index."""
    p = [(b >> (6-2*i)) & 3 for i in range(4)]
    p = [v if v != 3 else 0 for v in p]  # 3 -> 0
    # Try standard ternary: MSB first
    return p[0]*27 + p[1]*9 + p[2]*3 + p[3]

# Check if our ternary formula matches table1
mismatches = [(b, pixel4_to_ternary(b), table1[b]) for b in range(256) if pixel4_to_ternary(b) != table1[b]]
print(f"Ternary formula mismatches: {len(mismatches)} of 256")
if mismatches[:5]:
    print(f"  First: {[(b, exp, got) for b,exp,got in mismatches[:5]]}")

# Try other orderings if mismatch
if mismatches:
    for order in [[0,1,2,3],[3,2,1,0],[1,0,3,2],[2,3,0,1]]:
        def f(b, ord=order):
            p = [(b >> (6-2*i)) & 3 for i in range(4)]
            p = [v if v != 3 else 0 for v in p]
            return p[ord[0]]*27 + p[ord[1]]*9 + p[ord[2]]*3 + p[ord[3]]
        mm = sum(1 for b in range(256) if f(b) != table1[b])
        if mm == 0:
            print(f"Correct order: {order}")
            pixel4_to_ternary = f
            break

# Build IWRAM table for given (c1, c2)
def build_iwram(c1, c2):
    """Build IWRAM table: for each ternary pattern (0-80), output VRAM halfword."""
    iwram = [0] * 81
    colors = [0, c1, c2]  # 0->'0 pixel', 1->c1, 2->c2
    for idx in range(81):
        # Decode ternary index to 4 pixel values
        tmp = idx
        pix = []
        for _ in range(4):
            pix.append(tmp % 3)
            tmp //= 3
        # pix[0] is LSB (first pixel), pix[3] is MSB (last pixel)
        # VRAM halfword: (pix3_c<<12)|(pix2_c<<8)|(pix1_c<<4)|pix0_c
        w = (colors[pix[3]] << 12) | (colors[pix[2]] << 8) | (colors[pix[1]] << 4) | colors[pix[0]]
        iwram[idx] = w
    return iwram

def compute_vram_tile(rom_off, iwram):
    """Convert ROM 2bpp tile (16 bytes) to VRAM 4bpp tile (32 bytes) using IWRAM table."""
    vram = bytearray(32)
    r2 = rom_off
    for i in range(16):
        if i % 2 == 0:
            rom_byte = ROM[r2 + 1]  # high byte
        else:
            rom_byte = ROM[r2]       # low byte
            r2 += 2
        idx = table1[rom_byte]
        w = iwram[idx]
        vram[i*2] = w & 0xFF
        vram[i*2+1] = (w >> 8) & 0xFF
    return vram

def compute_fp(rom_page, idx_byte, iwram):
    base = FONT_BASE + rom_page * 0x2000 + idx_byte * 32
    tl = compute_vram_tile(base + 0, iwram)
    tr = compute_vram_tile(base + 16, iwram)
    bl = compute_vram_tile(base + 256, iwram)
    br = compute_vram_tile(base + 256 + 16, iwram)
    return hashlib.sha256(bytes(tl)+bytes(tr)+bytes(bl)+bytes(br)).hexdigest()[:16]

# Known ROM positions (from glyph_table, confirmed reliable ones)
ko = json.load(open("app/src/main/assets/moneo/ko_charmap.json"))
ko_by_char = {v: k for k, v in ko.items()}

# Known mappings (visually/OCR confirmed)
known = {
    '하': (1, 178),   # visually confirmed
    '가': (1, 102),   # visually confirmed  
    '나': (1, 91),    # from new_map (glyph_table)
    '다': (2, 40),
    '로': (2, 38),
    '를': (3, 167),
    '이': (1, 98),
    '만': (1, 87),
    '그': (1, 39),
    '니': (1, 207),
    '기': (1, 56),
    '을': (1, 70),
    '나': (1, 91),
}

# Filter to those in ko_charmap
test_cases = {ch: pos for ch, pos in known.items() if ch in ko_by_char}
print(f"\nTest cases with ko_charmap entries: {len(test_cases)}")

# Brute force (c1, c2)
print("\nBrute-forcing c1,c2...")
best_matches = 0
best_params = None
for c1 in range(1, 16):
    for c2 in range(1, 16):
        if c1 == c2:
            continue
        iwram = build_iwram(c1, c2)
        matches = 0
        for ch, (p, idx) in test_cases.items():
            if ch not in ko_by_char:
                continue
            fp = compute_fp(p, idx, iwram)
            exp = ko_by_char[ch]
            if fp == exp:
                matches += 1
        if matches > best_matches:
            best_matches = matches
            best_params = (c1, c2)
            print(f"  New best: c1={c1}, c2={c2} -> {matches}/{len(test_cases)} matches")

print(f"\nBest: c1={best_params}, matches={best_matches}/{len(test_cases)}")

if best_params:
    c1, c2 = best_params
    iwram = build_iwram(c1, c2)
    print("\nVerifying all test cases:")
    for ch, (p, idx) in test_cases.items():
        if ch not in ko_by_char:
            continue
        fp = compute_fp(p, idx, iwram)
        exp = ko_by_char[ch]
        match = '✓' if fp == exp else '✗'
        print(f"  {ch}: {match} computed={fp} expected={exp}")
