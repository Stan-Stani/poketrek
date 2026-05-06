#!/usr/bin/env python3
"""End-to-end blit verification:
  1. For each token in capture, compute the (page, idx) glyph via blit (layout B).
  2. Hash the 4 sub-tiles (TL, TR, BL, BR) -> 128-byte SHA-256.
  3. Compare to the fingerprints recorded in groups co-occurring with the token.

Try every sub-tile permutation; report the best agreement.
"""
import json, struct, hashlib
from itertools import permutations
from pathlib import Path
from collections import defaultdict, Counter

ROM = bytes(Path("Pocket Monsters - LeafGreen (Korean).gba").read_bytes())
IWRAM = bytes(Path(".moneo-artifacts/dumps/iwram.bin").read_bytes())
FONT_BASE = 0x780000

table1 = ROM[0x1CDF1C : 0x1CDF1C + 256]
table2 = struct.unpack_from("<256H", IWRAM, 0x0A40)


def blit_subtile(rom_off):
    out = bytearray(32)
    for k in range(8):
        b0 = ROM[rom_off + k * 2]
        b1 = ROM[rom_off + k * 2 + 1]
        v0 = table2[table1[b0]]
        v1 = table2[table1[b1]]
        # layout B: b1 first, little-endian halfwords
        out[k*4+0] = v1 & 0xFF; out[k*4+1] = (v1>>8)&0xFF
        out[k*4+2] = v0 & 0xFF; out[k*4+3] = (v0>>8)&0xFF
    return bytes(out)


def fp_glyph(p, idx, perm):
    base = FONT_BASE + p*0x2000 + idx*32
    sub = [blit_subtile(base+0), blit_subtile(base+16),
           blit_subtile(base+256), blit_subtile(base+272)]
    blob = b''.join(sub[i] for i in perm)
    return hashlib.sha256(blob).hexdigest()[:16]


cap = json.load(open('.moneo-artifacts/capture-bp6.json'))
tokens = cap['tokens']
groups = cap['groups']
print(f"tokens={len(tokens)} groups={len(groups)}")

# Build frame -> set of fps
from bisect import bisect_left, bisect_right
fp_by_frame = defaultdict(set)
for g in groups:
    for fp in g['fps']:
        fp_by_frame[g['frame']].add(fp)
sorted_frames = sorted(fp_by_frame)
print(f"unique snapshot frames: {len(sorted_frames)}")

def fps_in_window(lo, hi):
    if lo > hi: return set()
    i = bisect_left(sorted_frames, lo)
    j = bisect_right(sorted_frames, hi)
    s = set()
    for k in range(i, j):
        s |= fp_by_frame[sorted_frames[k]]
    return s

POST = 5  # very tight window

# Best perm: agreement = number of tokens whose computed fp is in post-window
best = (-1, None)
for perm in permutations(range(4)):
    agreed = 0
    seen_keys = set()
    for t in tokens:
        key = (t['page'], t['idx'])
        if key in seen_keys:
            continue
        seen_keys.add(key)
        fp = fp_glyph(t['page'], t['idx'], perm)
        # check first occurrence of this token
        nearby = fps_in_window(t['frame'], t['frame']+POST)
        if fp in nearby:
            agreed += 1
    print(f"  perm={perm} agreed={agreed}/{len(seen_keys)}")
    if agreed > best[0]:
        best = (agreed, perm)
print(f"\nBest: perm={best[1]} agreed={best[0]}")
