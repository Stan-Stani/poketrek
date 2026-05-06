#!/usr/bin/env python3
"""Verify blit by computing the 32-byte VRAM for a known sub-tile and
comparing to a live VRAM tile.

Strategy: token (page=4, idx=A6=166) was hit 79 times in capture-bp5. Whatever
glyph it draws must, post-render, exist as 4 sub-tiles in some BG charblock.
We compute via blit and search the ENTIRE VRAM dump for a 32-byte match.
If nothing matches, the blit byte-order assumption is wrong.
"""
import struct, hashlib
from pathlib import Path

ROM = bytes(Path("Pocket Monsters - LeafGreen (Korean).gba").read_bytes())
IWRAM = bytes(Path(".moneo-artifacts/dumps/iwram.bin").read_bytes())
VRAM = bytes(Path(".moneo-artifacts/dumps/vram.bin").read_bytes())
FONT_BASE = 0x780000

# Note: VRAM is from BEFORE the long capture (savestate-load time, on title screen).
# So glyphs from in-game won't be there. But basic UI text (menus) might be.

table1 = ROM[0x1CDF1C : 0x1CDF1C + 256]
table2 = struct.unpack_from("<256H", IWRAM, 0x0A40)


def blit_subtile(rom_off, layout):
    """layout: 'A' = byte0,byte1 in halfword order;
              'B' = byte1,byte0 (left-first);
              'C' = byte0,byte1 swapped within halfword;
              'D' = byte1,byte0 swapped within halfword.
    Returns 32 bytes."""
    out = bytearray(32)
    for k in range(8):
        b0 = ROM[rom_off + k * 2]
        b1 = ROM[rom_off + k * 2 + 1]
        v0 = table2[table1[b0]]
        v1 = table2[table1[b1]]
        if layout == 'A':
            # b0 first (low addr first), little-endian halfword bytes
            out[k*4+0] = v0 & 0xFF; out[k*4+1] = (v0>>8)&0xFF
            out[k*4+2] = v1 & 0xFF; out[k*4+3] = (v1>>8)&0xFF
        elif layout == 'B':
            # b1 first
            out[k*4+0] = v1 & 0xFF; out[k*4+1] = (v1>>8)&0xFF
            out[k*4+2] = v0 & 0xFF; out[k*4+3] = (v0>>8)&0xFF
        elif layout == 'C':
            # b0 first, big-endian halfword bytes
            out[k*4+0] = (v0>>8)&0xFF; out[k*4+1] = v0 & 0xFF
            out[k*4+2] = (v1>>8)&0xFF; out[k*4+3] = v1 & 0xFF
        elif layout == 'D':
            # b1 first, big-endian halfword bytes
            out[k*4+0] = (v1>>8)&0xFF; out[k*4+1] = v1 & 0xFF
            out[k*4+2] = (v0>>8)&0xFF; out[k*4+3] = v0 & 0xFF
    return bytes(out)


def find_in_vram(needle):
    pos = []
    i = 0
    while True:
        j = VRAM.find(needle, i)
        if j < 0: break
        pos.append(j)
        i = j + 1
    return pos


def render_glyph_pillar(p, idx, layout):
    base = FONT_BASE + p * 0x2000 + idx * 32
    return [blit_subtile(base + 0, layout),
            blit_subtile(base + 16, layout),
            blit_subtile(base + 256, layout),
            blit_subtile(base + 272, layout)]


# Try every (page, idx) from common UI text (probably page 1-3, lots of common chars)
# Look for whole-glyph matches in VRAM
print(f"VRAM size: {len(VRAM)} (covers CB0..CB5 ish)")
print(f"Searching VRAM for any (page, idx) sub-tile content under layouts A,B,C,D...")

best_count = {}
for layout in 'ABCD':
    hits = 0
    samples = []
    for p in range(1, 7):
        for idx in range(256):
            sub = blit_subtile(FONT_BASE + p*0x2000 + idx*32, layout)
            # skip blank
            if all(b == sub[0] for b in sub):
                continue
            poses = find_in_vram(sub)
            if poses:
                hits += 1
                if len(samples) < 5:
                    samples.append((p, idx, poses[0]))
    best_count[layout] = hits
    print(f"  layout={layout}: {hits} sub-tiles found in VRAM. Samples: {samples}")

print(f"\nBest layout: {max(best_count, key=best_count.get)} ({best_count})")
