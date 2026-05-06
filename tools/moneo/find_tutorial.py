#!/usr/bin/env python3
"""Search ROM corpus for tutorial text and identify unknown char positions."""
import json
from pathlib import Path

raw = json.load(open('.moneo-artifacts/rom-text-ko-raw.json'))
gm = json.load(open('tools/moneo/glyph-map.json'))
new_map = gm['map']

# Build reverse map: char -> ROM keys
char_to_rom = {}
for k, v in new_map.items():
    char_to_rom.setdefault(v, []).append(k)

# Decode a record using new_map
def decode(hex_str):
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
        elif b == 0xFA:  # scroll
            out.append('\n')
            i += 1
        elif b == 0xFB:  # clear
            out.append('\n\n')
            i += 1
        elif b == 0xFE:  # newline
            out.append('\n')
            i += 1
        elif b in (0xFC, 0xFD) and i+1 < len(bs):
            i += 2
        else:
            i += 1
    return ''.join(out)

# Find records containing 하 (F1,178) and 로 (F2,38)
# 하 = F1,178 -> bytes 0xF1, 178 = 0xF1 0xB2
# 로 = F2,38 -> bytes 0xF2, 38 = 0xF2 0x26
print("Looking for tutorial text...")
tut_chars = '상하좌우로움직이거나항목을선택합니다'

for rec in raw['records'][:]:
    bs = bytes.fromhex(rec['hex'])
    # Check if 하 (0xF1, 0xB2) appears
    if bytes([0xF1, 178]) in bs:
        decoded = decode(rec['hex'])
        # Check if it looks like tutorial
        if any(c in decoded for c in ['좌', '우', '상']):
            print(f"TUTORIAL CANDIDATE id={rec.get('id','?')}:")
            print(f"  {decoded[:80]!r}")
            print(f"  hex: {rec['hex'][:60]}...")
            # Print byte-by-byte decode
            i = 0
            print("  Tokens: ", end='')
            while i < len(bs):
                b = bs[i]
                if b == 0xFF: break
                if 0xF1 <= b <= 0xF6 and i+1 < len(bs):
                    p = b - 0xF0
                    idx = bs[i+1]
                    key = f'F{p},{idx}'
                    ch = new_map.get(key, f'[{key}]')
                    print(f'{ch!r}', end=' ')
                    i += 2
                elif b in (0xFA, 0xFB, 0xFE):
                    i += 1
                elif b in (0xFC, 0xFD) and i+1 < len(bs):
                    i += 2
                else:
                    i += 1
            print()
            print()

# Also find records with many [F?,?] unknowns to understand coverage
print("Records with 하 but no other identified chars:")
count = 0
for rec in raw['records'][:200]:
    bs = bytes.fromhex(rec['hex'])
    if bytes([0xF1, 178]) in bs:
        decoded = decode(rec['hex'])
        known = sum(1 for c in decoded if not c.startswith('[') and c not in '\n')
        total = sum(1 for c in decoded if c not in '\n')
        if total > 0:
            print(f"  id={rec.get('id','?')}: {decoded[:50]!r} ({known}/{total} known)")
            count += 1
            if count >= 5:
                break
