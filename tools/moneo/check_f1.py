#!/usr/bin/env python3
import json

gt = json.load(open('.moneo-artifacts/glyph-table.json'))
# Check F1 second half (gids 256-511) - accessible via ROM 0xF1
print('F1 gids 256-280:')
for g in range(256, 281):
    v = gt.get(f'F1,{g}')
    if v:
        print(f'  F1,{g}={v!r}')

print('\nAround 가 (F1,358):')
for g in range(350, 370):
    v = gt.get(f'F1,{g}')
    print(f'  F1,{g}={v!r}')

print('\nAround 하 (F1,434):')
for g in range(430, 440):
    v = gt.get(f'F1,{g}')
    print(f'  F1,{g}={v!r}')

# Check the char '꿱'
kq = [k for k, v in gt.items() if v == '꿱']
print(f'\n꿱 positions in glyph_table: {kq[:5]}')

# Now check: what's in F1,358 where I expect 가?
print(f'\nF1,358: {gt.get("F1,358")!r}')

# Print full F1 second half non-blank entries
print('\nAll non-blank F1 gids 256-511:')
for g in range(256, 512):
    v = gt.get(f'F1,{g}')
    if v:
        print(f'  {g}:{v!r}', end='')
print()
