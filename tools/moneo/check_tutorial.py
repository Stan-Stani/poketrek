#!/usr/bin/env python3
"""Find tutorial chars in glyph-table and check render_dialogue approach."""
import json
from pathlib import Path

ks = json.load(open('.moneo-artifacts/ksx1001-charmap.json'))
gt = json.load(open('.moneo-artifacts/glyph-table.json'))
raw = json.load(open('.moneo-artifacts/rom-text-ko-raw.json'))

# Find chars from the tutorial line in glyph-table
target = '상하좌우로움직이거나항목을선택합니다'
print('Tutorial chars in glyph-table:')
for c in target:
    hits = [k for k,v in gt.items() if v==c]
    print(f'  {c!r}: {hits[:5]}')

print()
# Also check ksx1001
print('Tutorial chars in ksx1001-charmap:')
for c in target:
    hits = [k for k,v in ks.items() if v==c]
    print(f'  {c!r}: {hits[:3]}')

# Now check render_dialogue approach:
# render_dialogue uses: FONT_BASE + page * 0x2000 + idx * 32
# This maps (rom_page, idx_byte) to (lp = rom_page, idx_font = idx_byte) in build_charmap terms
# Where lp = rom_page directly, idx = idx_byte directly
# And glyph_table key is F{lp},{idx_font} (where lp starts at 1 for Korean)
# But glyph_table uses page 1-6 for F1-F6 which are 0x4000-spaced
# While render_dialogue uses lp 1-6 which are 0x2000-spaced
# So render_dialogue(page, idx) corresponds to glyph_table F? based on:
# render_dialogue offset = FONT_BASE + page*0x2000 + idx*32
# glyph_table F{p},g offset = FONT_BASE + (p-1)*0x4000 + g*32
# Setting equal: page*0x2000 + idx*32 = (p-1)*0x4000 + g*32
# page*0x2000/0x4000 = (p-1) + (g-idx)*32/0x4000
# If page is odd: page = 2*(p-1)+1 -> p = (page+1)/2, but only for odd page
# For page=1: (p-1) = 0.5, not integer -> p is F1 second half
# Actually: FONT_BASE + page*0x2000 = FONT_BASE + (p-1)*0x4000 + extra
# extra = page*0x2000 - (p-1)*0x4000
# For page=1: extra = 0x2000 - 0 = 0x2000 -> within F1, lp offset 0x2000
# In glyph_table F1 terms: g = (0x2000 + idx*32) / 32 = 64 + idx
# So render_dialogue(page=1, idx) = glyph_table("F1", 64+idx)
print()
print("Mapping render_dialogue(page, idx) -> glyph_table:")
# For render_dialogue page=1: gt key = F1,{64+idx}
# For render_dialogue page=2: FONT_BASE+2*0x2000 = FONT_BASE+0x4000
#   = FONT_BASE + (2-1)*0x4000 + 0 -> F2,{0+idx} = F2,idx
# For render_dialogue page=3: FONT_BASE+3*0x2000 = FONT_BASE+0x6000
#   = FONT_BASE + (2-1)*0x4000 + 0x2000 -> F2,{64+idx}... or
#   = FONT_BASE + 1*0x4000 + 0x2000 -> F2, {64+idx}  (p=2, extra=0x2000)
# For render_dialogue page=4: FONT_BASE+4*0x2000=FONT_BASE+0x8000=(p=3)*0x4000 -> F3,idx
# For render_dialogue page=5: FONT_BASE+5*0x2000=FONT_BASE+0xA000=(p=3)*0x4000+0x2000 -> F3,{64+idx}
# For render_dialogue page=6: FONT_BASE+6*0x2000=FONT_BASE+0xC000=(p=4)*0x4000 -> F4,idx
# Pattern: gt_page = (render_page + 1) // 2, gt_offset_within_page = ((render_page % 2) * 64) + idx
def rd_to_gt(rd_page, idx):
    gt_page = (rd_page + 1) // 2
    gt_idx = ((rd_page % 2) * 64) + idx
    return f"F{gt_page},{gt_idx}"

# Test with known chars: 하 at glyph_table F1,434
# -> rd_page, idx s.t. gt=(F1,434): gt_page=1 -> rd_page=1 or 2 (odd)
# rd_page=1: gt_page=1, gt_idx=64+idx=434 -> idx=370 -> rd(1,370)=하
# rd_page=0: gt_page=0.5? invalid
print(f"  하=F1,434: rd(1,{434-64}) -> {rd_to_gt(1, 434-64)}")
print(f"  가=F1,10: rd(1,{10-64}) -> (invalid)")

# Look for 가 in glyph_table with smaller gid
for gid in range(300):
    if gt.get(f'F1,{gid}') == '가':
        print(f"  가 found at F1,{gid}")
        rd_page = 1
        idx = gid - 64
        print(f"  -> rd(1, {idx}) = 가")
        break

# Find what renders as the tutorial line from render_dialogue v8
# The tutorial line likely has: 상, 하, 좌, 우, 로, 움, 직, 이, 거, 나, 항, 목, 을, 선, 택, 합, 니, 다
# These are ROM pages 1-6 with specific idx values

# Let's check: in render_dialogue approach, 하 from ROM byte (0xF1, idx=?):
# For rd_page=1, glyph 하=gt("F1,?") where F1,?='하':
ha_gid = [int(k.split(',')[1]) for k,v in gt.items() if k.startswith('F1,') and v=='하']
print(f"\n하 gid positions in F1: {ha_gid[:10]}")
for gid in ha_gid[:3]:
    idx = gid - 64  # for rd_page=1
    if 0 <= idx <= 255:
        print(f"  rd(1,{idx}) -> F1,{gid} = 하")
