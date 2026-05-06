#!/usr/bin/env python3
"""Find the offset between ksx1001-charmap and glyph-table indexing,
then build the definitive ROM (page, idx_byte) -> Korean char mapping."""
import json, struct, hashlib
from pathlib import Path

gt = json.load(open('.moneo-artifacts/glyph-table.json'))
ks = json.load(open('.moneo-artifacts/ksx1001-charmap.json'))
ko = json.load(open('app/src/main/assets/moneo/ko_charmap.json'))

# Find offset between ksx1001 (F1,0=가) and glyph-table (F1,10=가)
print("=== Finding offset between ksx1001-charmap and glyph-table ===")
best_offset = 0
best_matches = 0
for offset in range(-20, 30):
    matches = 0
    for n in range(200):
        ks_key = f'F1,{n}'
        gt_key = f'F1,{n + offset}'
        ks_ch = ks.get(ks_key)
        gt_ch = gt.get(gt_key)
        if ks_ch and gt_ch and ks_ch == gt_ch:
            matches += 1
    if matches > best_matches:
        best_matches = matches
        best_offset = offset

print(f"Best offset (ks + offset = gt): {best_offset} with {best_matches}/200 matches")

# Verify with offset
print("\nSample comparison at best offset:")
for n in range(0, 20):
    ks_key = f'F1,{n}'
    gt_key = f'F1,{n + best_offset}'
    print(f"  ks[{ks_key}]={ks.get(ks_key,'?')!r} vs gt[{gt_key}]={gt.get(gt_key,'?')!r}")

# The glyph-table key F{page},{gid} uses:
# gid = the index such that goff(gid) = font_byte_offset_within_page
# goff(gid) = 0x200*(gid//16) + 0x20*(gid%16) = 0x20*gid = 32*gid
# page = 1..6 = rom_page

# From the runtime: font_byte_offset = (idx_byte>>4)*0x200 + (idx_byte&0xF)*0x10
# Setting equal to 32*gid:
# (idx_byte>>4)*0x200 + (idx_byte&0xF)*0x10 = 32*gid
# 16*(h*32 + l) = 32*gid where h=idx_byte>>4, l=idx_byte&0xF
# gid = (h*32 + l) / 2 -- integer only for even l

# For ODD l: gid is non-integer, meaning the runtime reads from the MIDDLE
# of a glyph entry. In that case, what does glyph_table give?
# It might still correspond to a valid Korean char if we consider the
# font layout differently.

# Let's just try: for all ROM (page, idx) pairs, compute gid candidate
# and look up in glyph_table. Then cross-check with ko_charmap.

print("\n=== Building ROM (page, idx_byte) -> Korean char mapping ===")
raw_data = json.loads(Path('.moneo-artifacts/rom-text-ko-raw.json').read_text())

# Collect all distinct (page, idx) from ROM corpus
token_set = set()
for rec in raw_data['records']:
    h = rec['hex']
    bs = bytes.fromhex(h)
    i = 0
    while i < len(bs):
        b = bs[i]
        if b == 0xFF: break
        if 0xF1 <= b <= 0xF6 and i+1 < len(bs):
            page = b - 0xF0
            idx = bs[i+1]
            token_set.add((page, idx))
            i += 2
        elif b in (0xFC, 0xFD) and i+1 < len(bs):
            i += 2
        else:
            i += 1

print(f"Distinct ROM tokens: {len(token_set)}")

# Build mapping using glyph_table
# gid = (h*32 + l) / 2 for even l
# For odd l: try gid = (h*32 + l - 1) / 2 (round down) -- might be wrong
translation = {}
even_count = 0
odd_count = 0
resolved = 0

for (page, idx_byte) in sorted(token_set):
    h = idx_byte >> 4
    l = idx_byte & 0xF
    gid_float = (h * 32 + l) / 2
    
    if l % 2 == 0:
        gid = h * 16 + l // 2
        even_count += 1
    else:
        # odd l: try gid = h*16 + (l-1)//2 (rounded down)
        # OR gid = h*16 + (l+1)//2 (rounded up)
        gid = h * 16 + (l - 1) // 2
        odd_count += 1
    
    gt_key = f'F{page},{gid}'
    ch = gt.get(gt_key)
    
    rom_key = f'F{page},{idx_byte}'
    if ch:
        translation[rom_key] = ch
        resolved += 1

print(f"Even l: {even_count}, Odd l: {odd_count}")
print(f"Resolved via glyph_table: {resolved}/{len(token_set)}")

# How many ko_charmap chars are in translation?
ko_chars = set(ko.values())
ko_in_translation = sum(1 for ch in translation.values() if ch in ko_chars)
print(f"ko_charmap chars found in translation: {ko_in_translation}")

# Check specific known chars
print("\nChecking known chars:")
# 하: we know from build_charmap anchor it's at lp=0, idx_font=17 in build_charmap
# which means gid=17 in glyph_table (same formula)
# And ROM idx_byte that gives gid=17:
# gid = h*16 + l//2 = 17 -> h=1, l//2=1 -> l=2 -> idx_byte = 0x12 = 18
# or with odd: h=1, (l-1)//2=1 -> l=3 -> idx_byte = 0x13
idx_for_ha_even = 0x12  # h=1, l=2 -> gid=17
idx_for_ha_odd = 0x13   # h=1, l=3 -> gid=17 (rounded down)
print(f"  F1,0x12=18 -> gid={1*16+2//2}=17 -> gt={gt.get('F1,17','?')!r}")
print(f"  F1,0x13=19 -> gid_round={1*16+(3-1)//2}=17 -> gt={gt.get('F1,17','?')!r}")

# Save the translation
Path('.moneo-artifacts/rom-translation.json').write_text(
    json.dumps(translation, ensure_ascii=False, indent=1)
)
print(f"\nSaved {len(translation)} entries to .moneo-artifacts/rom-translation.json")
