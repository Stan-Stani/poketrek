#!/usr/bin/env python3
import json, sys

gt = json.load(open('.moneo-artifacts/glyph-table.json'))
ks = json.load(open('.moneo-artifacts/ksx1001-charmap.json'))

missing = ['상','선','좌','직','택','항','합','아','용','움','정','계','。']
print('Missing chars - ksx1001 vs glyph_table entries:')
for ch in missing:
    ks_pos = [k for k,v in ks.items() if v==ch]
    gt_pos = [k for k,v in gt.items() if v==ch]
    print(f'  {ch!r}: ksx1001={ks_pos[:2]} gt={gt_pos[:3]}')

# Also check total glyph_table size per page
from collections import Counter
page_cnt = Counter()
for k,v in gt.items():
    page_cnt[k.split(',')[0]] += 1
print('\nglyph_table entries per page:', sorted(page_cnt.items()))

# Check glyph_table entries near F3,92 (where 상 should be)
print('\nglyph_table F3 gids 88..96:')
for gid in range(88, 97):
    k = f'F3,{gid}'
    print(f'  F3,{gid}: {gt.get(k)!r}')

# Check glyph_table entries near F3,92 in ROM corpus
raw = json.load(open('.moneo-artifacts/rom-text-ko-raw.json'))
# Find all ROM tokens for page=4 (0xF4), which maps to F3,gid
page4_tokens = {}
for rec in raw['records']:
    bs = bytes.fromhex(rec['hex'])
    i = 0
    while i < len(bs):
        b = bs[i]
        if b == 0xFF: break
        if b == 0xF4 and i+1 < len(bs):
            idx = bs[i+1]
            page4_tokens[idx] = page4_tokens.get(idx, 0) + 1
            i += 2
        elif b in (0xFC, 0xFD) and i+1 < len(bs):
            i += 2
        else:
            i += 1

print(f'\nROM page=4 (0xF4) token count: {len(page4_tokens)} distinct idx values')
print(f'  idx=92 (->F3,92=상?) count: {page4_tokens.get(92, 0)}')
# gid=92 would be rom(page=4, idx=92)
