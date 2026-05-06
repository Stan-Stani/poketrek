#!/usr/bin/env python3
"""Attempt to compute VRAM fingerprints from ROM glyph data using blit table."""
import json
import hashlib
from pathlib import Path

ROM = bytearray(Path("Pocket Monsters - LeafGreen (Korean).gba").read_bytes())
FONT_BASE = 0x780000

# Blit lookup table from ROM at 0x081CDF1C (file offset 0x1CDF1C)
# The session notes say: [0,1,2,0,3,4,5,3,6,7,8,6,0,1,2,0,...]
blit_table_off = 0x1CDF1C
blit_table = list(ROM[blit_table_off: blit_table_off + 64])
print(f"Blit table (first 32 bytes): {blit_table[:32]}")

# The simplest interpretation: table maps 2bpp pixel value (0-3) -> 4bpp value
# From table[0..3] = [0,1,2,0]: pixel value 3 maps to 0 (background)
# So: 0->0, 1->1, 2->2, 3->0
# This makes the conversion reversible for pixel values 0-2

def rom_2bpp_tile_to_vram_4bpp(rom_off, tile_col_off=0, tile_row_off=0):
    """Convert ROM 2bpp tile to VRAM 4bpp tile (32 bytes).
    
    ROM 2bpp tile: 16 bytes (8 rows × 2 bytes/row, but in GBA 2bpp each row is 2 bytes for 8px)
    Wait: GBA uses 4bpp tiles (32 bytes), not 2bpp. Let me reconsider.
    
    The ROM Korean font is stored in a custom 2bpp format.
    ROM tile: 8×8 pixels × 2bpp = 16 bytes per tile.
    VRAM tile: 8×8 pixels × 4bpp = 32 bytes per tile.
    
    Conversion: each 2bpp pixel value v -> 4bpp value table[v]
    """
    # Extract pixels from ROM tile
    # Each row is 2 bytes for 8 pixels (2bpp: 4 pixels per byte)
    # Byte order: GBA 2bpp format
    vram_tile = bytearray(32)
    
    for row in range(8):
        rom_row_off = rom_off + row * 2
        for half in range(2):
            # half=0: left 4 pixels, half=1: right 4 pixels
            b = ROM[rom_row_off + (1 - half)]  # Note: reversed byte order from render_glyph
            pixels = []
            for px in range(4):
                v = (b >> ((3 - px) * 2)) & 0x3
                pixels.append(v)
            # Map through blit table: use first 4 entries
            mapped = [blit_table[min(v, 15)] for v in pixels]
            # Pack into VRAM 4bpp: 2 pixels per byte
            vram_byte_start = row * 4 + half * 2
            # pixels: [p0, p1, p2, p3] -> VRAM bytes [p1|p0, p3|p2]
            vram_tile[vram_byte_start]     = (mapped[1] << 4) | mapped[0]
            vram_tile[vram_byte_start + 1] = (mapped[3] << 4) | mapped[2]
    return vram_tile

def compute_fingerprint(rom_page, idx_byte):
    """Compute VRAM fingerprint for ROM glyph at (rom_page, idx_byte).
    
    Glyph layout in ROM (2bpp):
    - Top-left tile at: FONT_BASE + rom_page*0x2000 + idx_byte*32 + 0
    - Top-right tile at: FONT_BASE + rom_page*0x2000 + idx_byte*32 + 16  
    - Bottom-left tile at: same+256 + 0
    - Bottom-right tile at: same+256 + 16
    
    VRAM fingerprint = SHA-256[:16] of TL_tile + TR_tile + BL_tile + BR_tile
    where each tile is 32 bytes of 4bpp data.
    """
    base = FONT_BASE + rom_page * 0x2000 + idx_byte * 32
    
    tl = rom_2bpp_tile_to_vram_4bpp(base)
    tr = rom_2bpp_tile_to_vram_4bpp(base + 16)  # TR tile is 16 bytes after TL
    bl = rom_2bpp_tile_to_vram_4bpp(base + 256)  # BL tile is 256 bytes after TL
    br = rom_2bpp_tile_to_vram_4bpp(base + 256 + 16)
    
    combined = bytes(tl) + bytes(tr) + bytes(bl) + bytes(br)
    return hashlib.sha256(combined).hexdigest()[:16]

# Test with known chars
ko = json.load(open("app/src/main/assets/moneo/ko_charmap.json"))
ko_by_char = {v: k for k, v in ko.items()}

print("\nTesting fingerprint computation for known chars:")
# Known: 하 = ROM(1, 178), 가 = ROM(1, 102)
known_rom = {
    '하': (1, 178),
    '가': (1, 102),  # confirmed visually
    '나': (1, 91),   # from new_map
    '다': (2, 40),   # from new_map
    '로': (2, 38),   # from new_map
}

for ch, (p, idx) in known_rom.items():
    computed_fp = compute_fingerprint(p, idx)
    expected_fp = ko_by_char.get(ch, 'NOT IN ko_charmap')
    match = '✓' if computed_fp == expected_fp else '✗'
    print(f"  {ch}: computed={computed_fp} expected={expected_fp} {match}")

# Also try matching ALL ROM tokens to ko_charmap fingerprints
print("\nTrying to match ROM tokens to ko_charmap fingerprints...")
gm = json.load(open('tools/moneo/glyph-map.json'))
raw = json.load(open('.moneo-artifacts/rom-text-ko-raw.json'))

# Collect distinct tokens
tokens = {}
for rec in raw['records']:
    bs = bytes.fromhex(rec['hex'])
    i = 0
    while i < len(bs):
        b = bs[i]
        if b == 0xFF: break
        if 0xF1 <= b <= 0xF6 and i+1 < len(bs):
            p = b - 0xF0
            idx = bs[i+1]
            tokens[(p, idx)] = tokens.get((p, idx), 0) + 1
            i += 2
        elif b in (0xFC, 0xFD) and i+1 < len(bs): i += 2
        else: i += 1

# Compute fingerprints for all tokens
fp_to_char = {v: k for k, v in ko.items()}
matches = {}
for (p, idx), cnt in tokens.items():
    fp = compute_fingerprint(p, idx)
    if fp in fp_to_char:
        matches[(p, idx)] = fp_to_char[fp]

print(f"Fingerprint matches: {len(matches)}/{len(tokens)}")
if matches:
    print("Matches:")
    for (p, idx), ch in sorted(matches.items()):
        print(f"  ROM(page={p}, idx={idx}) = {ch!r} (fp={compute_fingerprint(p,idx)})")
