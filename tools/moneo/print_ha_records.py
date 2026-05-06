#!/usr/bin/env python3
"""Print all records containing 하 to check for tutorial text."""
import json
from pathlib import Path

raw = json.load(open('.moneo-artifacts/rom-text-ko-raw.json'))
gm = json.load(open('tools/moneo/glyph-map.json'))
nm = gm['map']

def dec(h):
    bs = bytes.fromhex(h)
    o = []
    i = 0
    while i < len(bs):
        b = bs[i]
        if b == 0xFF: break
        if 0xF1 <= b <= 0xF6 and i+1 < len(bs):
            p = b - 0xF0
            idx = bs[i+1]
            k = f'F{p},{idx}'
            ch = nm.get(k, f'[{p},{idx}]')
            o.append(ch)
            i += 2
        elif b == 0xFE: o.append('\n'); i += 1
        elif b in (0xFA, 0xFB): o.append('|'); i += 1
        elif b in (0xFC, 0xFD) and i+1 < len(bs): i += 2
        else: i += 1
    return ''.join(o)

def token_seq(h):
    """Return list of (page, idx) tokens."""
    bs = bytes.fromhex(h)
    toks = []
    i = 0
    while i < len(bs):
        b = bs[i]
        if b == 0xFF: break
        if 0xF1 <= b <= 0xF6 and i+1 < len(bs):
            toks.append((b-0xF0, bs[i+1]))
            i += 2
        elif b in (0xFC, 0xFD) and i+1 < len(bs): i += 2
        else: i += 1
    return toks

HA_BYTE = bytes([0xF1, 178])
count = 0
for r in raw['records']:
    if HA_BYTE.hex() in r['hex']:
        toks = token_seq(r['hex'])
        decoded = dec(r['hex'])
        print(f"--- Record (contains 하 at F1,178) ---")
        print(f"  Raw tokens: {toks}")
        print(f"  Decoded: {decoded!r}")
        print()
        count += 1

print(f"Total records with 하: {count}")

# Also search for tutorial: look for the sequence 하 + next_char
# The tutorial has 상하좌우로 -> 상 THEN 하 THEN 좌 THEN 우 THEN 로
# Let's find records where 하 (F1,178) appears and what comes before/after it
print("\nContext around 하 in each record:")
for r in raw['records']:
    toks = token_seq(r['hex'])
    for j, (p, idx) in enumerate(toks):
        if p == 1 and idx == 178:
            before = toks[max(0,j-2):j]
            after = toks[j+1:min(len(toks),j+3)]
            before_dec = [nm.get(f'F{bp},{bi}', f'[{bp},{bi}]') for bp,bi in before]
            after_dec = [nm.get(f'F{bp},{bi}', f'[{bp},{bi}]') for bp,bi in after]
            print(f"  ...{before_dec} [하] {after_dec} ...")
