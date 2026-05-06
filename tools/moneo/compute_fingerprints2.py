#!/usr/bin/env python3
"""Understand the blit function and compute VRAM fingerprints correctly."""
import struct, hashlib, json
from pathlib import Path

ROM = bytearray(Path("Pocket Monsters - LeafGreen (Korean).gba").read_bytes())
FONT_BASE = 0x780000

# Read the two table pointers embedded in the blit function
# ldr r5, [pc, #0x10] at 0x8002f62: PC=0x8002f64 -> addr=0x8002f74
ptr_r5 = struct.unpack_from('<I', ROM, 0x2F74)[0]  # GBA address -> r5
# ldr r4, [pc, #0x10] at 0x8002f64: PC=0x8002f68 -> addr=0x8002f78
ptr_r4 = struct.unpack_from('<I', ROM, 0x2F78)[0]  # GBA address -> r4

print(f"r5 (word_table2) pointer: {ptr_r5:#010x}")
print(f"r4 (index_table1) pointer: {ptr_r4:#010x}")

def gba_to_file(gba_addr):
    if gba_addr >= 0x08000000:
        return gba_addr - 0x08000000
    raise ValueError(f"Unexpected GBA addr: {gba_addr:#x}")

off_r5 = gba_to_file(ptr_r5)
off_r4 = gba_to_file(ptr_r4)
print(f"r5 file offset: {off_r5:#x}")
print(f"r4 file offset: {off_r4:#x}")

# r4 = index_table1: for each ROM byte (0-255), gives an index
# r5 = word_table2: for each index, gives a 16-bit VRAM word
table1 = ROM[off_r4: off_r4+256]
print(f"\nTable1 (first 32 entries): {list(table1[:32])}")

# How many unique values in table1?
t1_unique = sorted(set(table1))
print(f"Table1 unique values: {len(t1_unique)}, range: {min(t1_unique)}-{max(t1_unique)}")

# Table2: 16-bit words, indexed by table1 values
max_t1 = max(t1_unique)
t2_size = (max_t1 + 1) * 2
table2_words = struct.unpack_from(f'<{max_t1+1}H', ROM, off_r5)
print(f"\nTable2 (first 16 words): {[hex(w) for w in table2_words[:16]]}")

def blit_byte(rom_byte):
    """Convert ROM byte (4 2bpp pixels) to VRAM halfword (4 4bpp pixels, 2 bytes)."""
    idx = table1[rom_byte]
    return table2_words[idx]

def compute_vram_tile(rom_off):
    """Convert 16-byte ROM 2bpp tile to 32-byte VRAM 4bpp tile using blit."""
    vram = bytearray(32)
    # Process 16 ROM bytes -> 16 VRAM halfwords (32 bytes)
    # The blit loop alternates: even iterations take high byte, odd take low byte
    # of consecutive 16-bit pairs from ROM
    r2 = rom_off  # ROM pointer
    for i in range(16):
        if i % 2 == 0:
            # Load 16-bit, take high byte (ROM[r2+1])
            rom_byte = ROM[r2 + 1]
        else:
            # Load byte at r2, then advance r2 by 2
            rom_byte = ROM[r2]
            r2 += 2
        vram_word = blit_byte(rom_byte)
        vram[i*2] = vram_word & 0xFF
        vram[i*2+1] = (vram_word >> 8) & 0xFF
    return vram

def rom_glyph_offset(rom_page, idx_byte):
    return FONT_BASE + rom_page * 0x2000 + idx_byte * 32

def compute_fingerprint(rom_page, idx_byte):
    base = rom_glyph_offset(rom_page, idx_byte)
    # Top half (16×8): two tiles TL and TR
    # TL at base+0 (16 bytes ROM), TR at base+16 (16 bytes ROM)
    # Bottom half at base+256: BL at base+256+0, BR at base+256+16
    tl = compute_vram_tile(base + 0)
    tr = compute_vram_tile(base + 16)
    bl = compute_vram_tile(base + 256)
    br = compute_vram_tile(base + 256 + 16)
    combined = bytes(tl) + bytes(tr) + bytes(bl) + bytes(br)
    return hashlib.sha256(combined).hexdigest()[:16]

# Test known chars
ko = json.load(open("app/src/main/assets/moneo/ko_charmap.json"))
ko_by_char = {v: k for k, v in ko.items()}

print("\nTesting fingerprints for known chars:")
known_rom = {
    '하': (1, 178),
    '가': (1, 102),
    '나': (1, 91),
    '다': (2, 40),
    '로': (2, 38),
    '를': (3, 167),
    '이': (1, 98),
    '하': (1, 178),
}
for ch, (p, idx) in known_rom.items():
    computed = compute_fingerprint(p, idx)
    expected = ko_by_char.get(ch, 'NOT IN ko_charmap')
    match = '✓' if computed == expected else '✗'
    print(f"  {ch}: computed={computed} expected={expected} {match}")

# Try all 1383 tokens
print("\nMatching all ROM tokens to ko_charmap...")
raw = json.load(open('.moneo-artifacts/rom-text-ko-raw.json'))
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

fp_to_char = {v: k for k, v in ko.items()}
matches = {}
for (p, idx) in tokens:
    fp = compute_fingerprint(p, idx)
    if fp in fp_to_char:
        matches[(p, idx)] = fp_to_char[fp]
print(f"Fingerprint matches: {len(matches)}/{len(tokens)}")
for (p, idx), ch in sorted(matches.items()):
    print(f"  ROM(page={p}, idx={idx}) = {ch!r}")
