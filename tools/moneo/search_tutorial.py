#!/usr/bin/env python3
"""Search for tutorial text using all known and guessed byte sequences."""
import json
from pathlib import Path

raw = json.load(open('.moneo-artifacts/rom-text-ko-raw.json'))
gm = json.load(open('tools/moneo/glyph-map.json'))
new_map = gm['map']

def decode_with_unknown(hex_str):
    bs = bytes.fromhex(hex_str)
    out = []
    i = 0
    while i < len(bs):
        b = bs[i]
        if b == 0xFF: break
        if 0xF1 <= b <= 0xF6 and i+1 < len(bs):
            p = b - 0xF0
            idx = bs[i+1]
            key = f'F{p},{idx}'
            ch = new_map.get(key, f'[{key}]')
            out.append(ch)
            i += 2
        elif b == 0xFE: out.append('\n'); i += 1
        elif b in (0xFA, 0xFB): out.append('|'); i += 1
        elif b in (0xFC, 0xFD) and i+1 < len(bs): i += 2
        else: i += 1
    return ''.join(out)

# Search for tutorial: look for records containing 하 AND 목 AND 을
# 하 = F1,178, 목 = F4,38 (4*16+38=102... wait)
# From new_map: 목 is at F4,38 or F6,230
# 을 is at F1,70 or F4,19 or F5,144
# 항 not found. Let me search by containing 하 + 목
print("Records with both 하 and 목:")
for rec in raw['records']:
    bs = bytes.fromhex(rec['hex'])
    has_ha = bytes([0xF1, 178]) in bs
    has_mok_1 = bytes([0xF4, 38]) in bs
    has_mok_2 = bytes([0xF6, 230]) in bs
    if has_ha and (has_mok_1 or has_mok_2):
        decoded = decode_with_unknown(rec['hex'])
        print(f"  id={rec.get('id','?')}: {decoded[:120]}")
        print(f"  hex: {rec['hex'][:80]}")
        print()

# Also: search for 상 at suspected positions
# 상 might be at F4,92 (glyph_table F3,92, but OCR said '디')
# OR 상 might be at a completely different position if glyph_table formula is wrong
print("\nSearching for patterns with 하+로:")
count = 0
for rec in raw['records']:
    bs = bytes.fromhex(rec['hex'])
    has_ha = bytes([0xF1, 178]) in bs
    has_ro1 = bytes([0xF2, 38]) in bs
    has_ro2 = bytes([0xF1, 14]) in bs
    has_ro3 = bytes([0xF3, 74]) in bs
    if has_ha and (has_ro1 or has_ro2 or has_ro3):
        decoded = decode_with_unknown(rec['hex'])
        print(f"  id={rec.get('id','?')}: {decoded[:100]}")
        count += 1
        if count >= 5: break
