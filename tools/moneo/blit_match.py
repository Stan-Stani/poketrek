#!/usr/bin/env python3
"""Path B: compute fingerprints for all (page, idx) and match against live
VRAM tile groups from a capture run. For the matched groups, OCR the FB at
their screen position to label the (page, idx).

Step 1: confirm blit-table layout (perm + hi_first) by matching against the
        88 verified entries in glyph-map.json AND against live captured fps.
Step 2: build (page, idx) -> char map by OCR'ing tile positions of matched
        groups in framebuffers.
"""
from __future__ import annotations
import hashlib, json, struct, subprocess, tempfile, os, re
from itertools import permutations
from pathlib import Path
from collections import Counter, defaultdict
from PIL import Image
from concurrent.futures import ProcessPoolExecutor, as_completed

ROM = bytes(Path("Pocket Monsters - LeafGreen (Korean).gba").read_bytes())
IWRAM = bytes(Path(".moneo-artifacts/dumps/iwram.bin").read_bytes())
FONT_BASE = 0x780000
table1 = ROM[0x1CDF1C : 0x1CDF1C + 256]
table2 = struct.unpack_from("<256H", IWRAM, 0x0A40)


def blit_tile_v(rom_off: int, hi_first: bool) -> bytes:
    out = bytearray(32)
    for hw in range(8):
        b0 = ROM[rom_off + hw * 2]; b1 = ROM[rom_off + hw * 2 + 1]
        first, second = (b1, b0) if hi_first else (b0, b1)
        v0 = table2[table1[first]]; v1 = table2[table1[second]]
        out[hw*4+0] = v0 & 0xFF; out[hw*4+1] = (v0>>8)&0xFF
        out[hw*4+2] = v1 & 0xFF; out[hw*4+3] = (v1>>8)&0xFF
    return bytes(out)


def glyph_subtile_offsets(p, i):
    base = FONT_BASE + p * 0x2000 + i * 32
    return [base, base+16, base+256, base+272]


def fingerprint_subtile(p, i, sub_idx, hi_first):
    offs = glyph_subtile_offsets(p, i)
    return hashlib.sha256(blit_tile_v(offs[sub_idx], hi_first)).hexdigest()[:16]


def fingerprint_4tile(p, i, perm, hi_first):
    offs = glyph_subtile_offsets(p, i)
    parts = [blit_tile_v(offs[k], hi_first) for k in perm]
    return hashlib.sha256(b"".join(parts)).hexdigest()[:16]


def find_layout():
    """Find best layout by matching captured group fps against computed fps."""
    cap = json.load(open(".moneo-artifacts/capture-walk.json"))
    groups = cap.get("groups", [])
    print(f"capture groups: {len(groups)}")
    # Collect all unique fps that appear in groups (as 4-tile concatenations or singletons)
    group_fps_singletons = set()
    group_fps_concat = set()
    for g in groups:
        for fp in g["fps"]:
            group_fps_singletons.add(fp)
        # 4-tile concat fp = sha256(concat 4 fp bytes)? Actually the capture
        # stores per-tile fps. Let's try matching sub-tiles.
    print(f"unique singleton tile fps: {len(group_fps_singletons)}")

    # For each (perm, hi_first) compute all per-subtile fps and count matches
    # against group_fps_singletons. Best layout is one with most matches.
    print("\n--- per-subtile single-tile fingerprint matching ---")
    best = None
    for hi_first in (False, True):
        for sub_idx in range(4):
            fps = set()
            for p in range(1, 7):
                for i in range(256):
                    fps.add(fingerprint_subtile(p, i, sub_idx, hi_first))
            matched = len(fps & group_fps_singletons)
            print(f"  hi_first={hi_first} sub={sub_idx}: {matched} of {len(group_fps_singletons)} live tile fps")
            if best is None or matched > best[0]:
                best = (matched, hi_first, sub_idx)
    matched, hi_first, sub_idx = best
    print(f"\nBest single-subtile layout: hi_first={hi_first} sub_idx={sub_idx} -> {matched} matches")
    return hi_first, sub_idx, group_fps_singletons


def main():
    hi_first, sub_idx, live_fps = find_layout()
    if not live_fps:
        return

    # Build fp -> (page, idx) mapping for the chosen sub-tile layout
    fp_to_pi = defaultdict(list)
    for p in range(1, 7):
        for i in range(256):
            fp = fingerprint_subtile(p, i, sub_idx, hi_first)
            fp_to_pi[fp].append((p, i))

    # Cross-check with verified glyph-map.json
    verified = json.load(open("tools/moneo/glyph-map.json"))["map"]
    print(f"\n--- cross-check against {len(verified)} verified (page,idx) ---")
    cross_match = 0
    for k, ch in verified.items():
        m = re.match(r"F(\d+),(\d+)", k)
        p, i = int(m.group(1)), int(m.group(2))
        fp = fingerprint_subtile(p, i, sub_idx, hi_first)
        if fp in live_fps:
            cross_match += 1
    print(f"verified entries whose fp appears live: {cross_match}/{len(verified)}")

    # Build inverse: live group fp -> (page, idx) candidate(s)
    live_resolvable = sum(1 for fp in live_fps if fp in fp_to_pi)
    print(f"live fps that map to a (page, idx): {live_resolvable}/{len(live_fps)}")

    # Save fingerprint table
    Path(".moneo-artifacts/blit-fp-table.json").write_text(json.dumps({
        "hi_first": hi_first, "sub_idx": sub_idx,
        "fp_by_pi": {f"F{p},{i}": fingerprint_subtile(p, i, sub_idx, hi_first)
                     for p in range(1, 7) for i in range(256)},
    }))
    print("Wrote .moneo-artifacts/blit-fp-table.json")


if __name__ == "__main__":
    main()
