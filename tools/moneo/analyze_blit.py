#!/usr/bin/env python3
"""Analyze the blit tables and try to infer the IWRAM color table."""
import struct, hashlib, json
from pathlib import Path

ROM = bytearray(Path("Pocket Monsters - LeafGreen (Korean).gba").read_bytes())
FONT_BASE = 0x780000

# Read table1 (index table at ROM 0x081CDF1C)
table1_off = 0x1CDF1C
table1 = ROM[table1_off: table1_off + 256]
print(f"Table1 first 32 bytes: {list(table1[:32])}")

# Key: table1 maps ROM byte -> index into IWRAM word table
# The IWRAM table has word[idx] = 4bpp pixel pair
# For background (ROM byte 0x00 = 4 zero pixels): table1[0x00] should map to index for (0,0) pair

# Analyze table1 unique indices
t1_unique = sorted(set(table1))
print(f"Table1 unique indices: {t1_unique}")
print(f"Table1 values: min={min(t1_unique)}, max={max(t1_unique)}, count={len(t1_unique)}")

# For 2bpp encoding: each byte has 4 pixels, 2 bits each
# ROM byte 0x00: all 4 pixels = 0 (background)  
# Let's analyze what ROM bytes map to what indices
print("\nTable1 analysis by pixel pattern:")
patterns = {}
for b in range(256):
    # Extract 4 2bpp pixels from byte
    # Render function uses: half=0: bits 7-4, half=1: bits 3-0 but reversed byte order
    # Actually from the blit: reads ROM byte directly (not reversed)
    # Pixels packed as: (b>>6)&3, (b>>4)&3, (b>>2)&3, (b>>0)&3
    p0 = (b >> 6) & 3
    p1 = (b >> 4) & 3
    p2 = (b >> 2) & 3
    p3 = (b >> 0) & 3
    key = (p0, p1, p2, p3)
    patterns[b] = (key, table1[b])

# Check: does all-zero bytes map to index 0?
print(f"  ROM byte 0x00 (all zeros): table1={table1[0x00]}")
print(f"  ROM byte 0xFF: pixels={(3,3,3,3)}, table1={table1[0xFF]}")
# Check specific values
for b in [0x00, 0x55, 0xAA, 0xFF, 0x01, 0x04, 0x10, 0x40]:
    p = ((b>>6)&3, (b>>4)&3, (b>>2)&3, (b>>0)&3)
    print(f"  ROM byte {b:#04x} pixels={p}: table1={table1[b]}")

# Now: what does IWRAM table look like?
# The blit writes: IWRAM_table[table1[ROM_byte]] to VRAM as a 16-bit halfword
# VRAM halfword = two 4bpp pixels: byte[1]<<8 | byte[0] but as 4bpp pair:
# low nibble = pixel 0, high nibble = pixel 1
# Since GBA is little-endian, halfword stored as [byte0, byte1]
# = [(pix1<<4)|pix0, (pix3<<4)|pix2] - wait let me think more carefully

# 4bpp tile: each byte contains 2 pixels: low nibble = left pixel, high nibble = right pixel
# A 16-bit halfword covers 4 pixels: byte0=(pix1<<4|pix0), byte1=(pix3<<4|pix2)

# Hypothesis: the IWRAM table entries directly correspond to 4bpp pixel pairs
# where the game uses colors: 0=background, 1=shadow, 2=main text, 3=outline?
# The known blit table notes say: [0,1,2,0,3,4,5,3,6,7,8,6,0,1,2,0,...]
# That was the TABLE1 content, not IWRAM content.

# Let me check if the IWRAM can be inferred from what the ROM glyph data IS
# If I know the glyph pixel pattern (from ROM) AND the VRAM output (from fingerprint capture),
# I can recover the IWRAM mapping.

# Known: ROM(page=1, idx=178) = 하 = ko_charmap fingerprint 2c43a50ca96aa9e3
# Let me read the ROM bytes for 하 and print them
base = FONT_BASE + 1 * 0x2000 + 178 * 32
print(f"\n하 ROM glyph at offset {base:#x}:")
print(f"  Top-left tile bytes (16): {[hex(b) for b in ROM[base:base+16]]}")
print(f"  Top-right tile bytes (16): {[hex(b) for b in ROM[base+16:base+32]]}")
print(f"  Bottom-left tile bytes (16): {[hex(b) for b in ROM[base+256:base+272]]}")
print(f"  Bottom-right tile bytes (16): {[hex(b) for b in ROM[base+272:base+288]]}")

# For each ROM byte in the glyph, what table1 index does it map to?
glyph_bytes = list(ROM[base:base+16]) + list(ROM[base+16:base+32]) + \
              list(ROM[base+256:base+272]) + list(ROM[base+272:base+288])
unique_in_glyph = set(glyph_bytes)
print(f"\nUnique ROM bytes in 하 glyph: {len(unique_in_glyph)}")
t1_values = {b: table1[b] for b in unique_in_glyph}
print(f"table1 indices for those bytes: {sorted(t1_values.values())}")

# The fingerprint sha256 is over the VRAM tile data (32 bytes per tile × 4 = 128 bytes)
# Each VRAM tile byte = (pix_right<<4) | pix_left
# For the blit output: strh (r0=[IWRAM_table[idx]]) to destination
# VRAM output is 16 halfwords (32 bytes) for a 16-byte ROM tile
# So each ROM byte -> 1 VRAM halfword = 2 VRAM bytes = 4 4bpp pixels

# But wait: GBA 4bpp tile has:
# - 32 bytes total for 8×8 pixels
# - 4 bytes per row = 8 pixels per row
# - Each byte: 2 pixels
# And the fingerprint uses sha256 of [tl(32) || tr(32) || bl(32) || br(32)]
# So total 128 bytes from 4 tiles

# The blit loop runs 16 times for 16 input bytes, producing 16 halfwords = 32 bytes
# This matches ONE 4bpp tile (32 bytes) from ONE 2bpp tile (16 bytes)
# So blit is called 4 times total for TL, TR, BL, BR tiles

# For a known 하 ROM glyph, if I assume a simple IWRAM table:
# Hypothesis 1: IWRAM_table[idx] = (idx << 4) | (idx << 12) for pixels
# Hypothesis 2: IWRAM_table[idx] = idx * 0x1111
# Let me try to BRUTE FORCE the IWRAM table by assuming it maps simply

# Key insight: ROM background pixels are value 0
# 0x00 ROM byte -> table1[0x00] -> IWRAM_table[that] -> should be 0x0000 (transparent pair)
bg_idx = table1[0x00]
print(f"\nBackground index: {bg_idx} (should map to 0x0000 in IWRAM)")
print(f"All ROM bytes that map to index {bg_idx}: {[b for b in range(256) if table1[b]==bg_idx]}")

# Since I can't access IWRAM, let me try a different approach:
# Use the render_verify.py's pixel output to build the expected VRAM tile
# and compute what IWRAM table would produce that from the ROM input

# OR: just use the glyph_table OCR results for chars that ARE correct, and 
# manually override the 13 known-wrong chars using visual inspection

print("\n\nConclusion: IWRAM table is not accessible offline. Using glyph_table + manual overrides.")
