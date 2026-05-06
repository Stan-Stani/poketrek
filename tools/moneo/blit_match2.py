#!/usr/bin/env python3
"""Path B v2: capture's group fps are sha256(4-tile concat, 128 bytes).
Compute matching 4-tile fingerprints for each (page, idx) and find layout."""
from __future__ import annotations
import hashlib, json, struct, re
from itertools import permutations
from pathlib import Path
from collections import defaultdict

ROM = bytes(Path("Pocket Monsters - LeafGreen (Korean).gba").read_bytes())
IWRAM = bytes(Path(".moneo-artifacts/dumps/iwram.bin").read_bytes())
FONT_BASE = 0x780000
table1 = ROM[0x1CDF1C : 0x1CDF1C + 256]
table2 = struct.unpack_from("<256H", IWRAM, 0x0A40)


def blit_tile_v(rom_off, hi_first):
    out = bytearray(32)
    for hw in range(8):
        b0 = ROM[rom_off + hw*2]; b1 = ROM[rom_off + hw*2 + 1]
        first, second = (b1, b0) if hi_first else (b0, b1)
        v0 = table2[table1[first]]; v1 = table2[table1[second]]
        out[hw*4+0] = v0 & 0xFF; out[hw*4+1] = (v0>>8)&0xFF
        out[hw*4+2] = v1 & 0xFF; out[hw*4+3] = (v1>>8)&0xFF
    return bytes(out)


def glyph_fp4(p, i, perm, hi_first):
    base = FONT_BASE + p * 0x2000 + i * 32
    offs_pool = [base, base+16, base+256, base+272]
    parts = [blit_tile_v(offs_pool[k], hi_first) for k in perm]
    return hashlib.sha256(b"".join(parts)).hexdigest()[:16]


def main():
    cap = json.load(open(".moneo-artifacts/capture-walk.json"))
    groups = cap["groups"]
    # Collect ALL 4-tile fps from groups (one per charblock per group)
    live_fps = set()
    for g in groups:
        for fp in g["fps"]:
            live_fps.add(fp)
    print(f"unique 4-tile group fps: {len(live_fps)}")

    print("\n--- searching layouts ---")
    best = None
    for hi_first in (False, True):
        for perm in permutations(range(4)):
            count = 0
            for p in range(1, 7):
                for i in range(256):
                    fp = glyph_fp4(p, i, perm, hi_first)
                    if fp in live_fps:
                        count += 1
            if best is None or count > best[0]:
                best = (count, perm, hi_first)
                if count >= 2:
                    print(f"  perm={perm} hi_first={hi_first}: {count}")
    matched, perm, hi_first = best
    print(f"\nBest layout: perm={perm} hi_first={hi_first} matches = {matched}")

    if matched < 2:
        print("\nNo layout matches. fp computation may be wrong (palette swap, byte order, ...).")
        return

    # Build full table
    fp_to_pi = defaultdict(list)
    for p in range(1, 7):
        for i in range(256):
            fp = glyph_fp4(p, i, perm, hi_first)
            fp_to_pi[fp].append((p, i))
    resolvable = sum(1 for fp in live_fps if fp in fp_to_pi)
    print(f"live fps resolvable to (page,idx): {resolvable}/{len(live_fps)}")

    Path(".moneo-artifacts/blit-fp4.json").write_text(json.dumps({
        "perm": list(perm), "hi_first": hi_first,
        "fp_to_pi": {fp: pis for fp, pis in fp_to_pi.items() if pis},
    }))
    print("Wrote .moneo-artifacts/blit-fp4.json")


if __name__ == "__main__":
    main()
