#!/usr/bin/env python3
"""Locate the rewritten glyph composer function.

The composer writes to the rendered-glyph cache at EWRAM 0x02007000..
0x02009000. Functions that touch that region have literal-pool entries
pointing into it. Scan all rewritten code (the rank-3 patch covers
file 0x6ccd2..0xb2e68 and contains the BL LZ77UnCompWram site at
0x9f850) for u32 values in the cache range, then look ±256 bytes for
the surrounding function's other literals — patched-region pointers
among them are the jamo atlas candidates.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter

ROM = Path(__file__).resolve().parent / "leafgreen_J-K_2024.gba"
GBA_BASE = 0x08000000
EWRAM_GLYPH_LO = 0x02007000
EWRAM_GLYPH_HI = 0x02009000
PATCHED_LO = 0x08D00000
PATCHED_HI = 0x09000000

# All the diff runs (file offsets) where the patch rewrote vanilla code.
# Take the top-N runs by length — rank 3, 4, 5, 16, 22, 23 cover the
# rewritten text engine.
REWRITTEN_RUNS = [
    (0x6ccd2,  0xb2e68,   "rank3"),
    (0xdc1fc,  0x120089,  "rank4"),
    (0x13f41d, 0x17d286,  "rank5"),
    (0xc432c,  0xdc1ee,   "rank16"),
    (0x2be2,   0x2973f,   "rank11"),
    (0x1308ee, 0x13f40f,  "rank23"),
    (0x3b660,  0x4b557,   "rank22"),
    (0x4b560,  0x59b05,   "rank24"),
    (0x180000, 0x200000,  "extended_search"),  # search broader to catch others
]


def main():
    data = ROM.read_bytes()
    print(f"Loaded {ROM.name}\n")

    # Collect every offset where a u32 read targets the glyph cache region.
    composer_anchors = []
    for run_start, run_end, label in REWRITTEN_RUNS:
        for off in range(run_start & ~3, run_end & ~3, 4):
            val = int.from_bytes(data[off:off + 4], "little")
            if EWRAM_GLYPH_LO <= val < EWRAM_GLYPH_HI:
                composer_anchors.append((off, val, label))

    print(f"u32 literals targeting EWRAM glyph cache (0x{EWRAM_GLYPH_LO:08x}..0x{EWRAM_GLYPH_HI:08x}):")
    print(f"  total: {len(composer_anchors)}")
    seen_vals = Counter(v for _, v, _ in composer_anchors)
    print(f"  distinct values: {len(seen_vals)}")
    for v, c in seen_vals.most_common(15):
        print(f"    {v:#x}: {c} occurrences")

    if not composer_anchors:
        print("\nNo direct hits — composer may use a base-pointer + offset scheme.")
        print("Falling back: search for u32 == 0x02000000 (EWRAM base) as the base pointer.")
        for run_start, run_end, label in REWRITTEN_RUNS:
            for off in range(run_start & ~3, run_end & ~3, 4):
                val = int.from_bytes(data[off:off + 4], "little")
                if val == 0x02000000:
                    composer_anchors.append((off, val, label))
        print(f"  total EWRAM-base hits: {len(composer_anchors)}")

    # For each anchor, look at the surrounding function (±200 bytes both
    # ways). Collect every other u32 literal that points at the patched
    # region (>= 0x08D00000).
    print("\n" + "=" * 70)
    print("Inspecting context around each composer anchor (function literals):")
    print("=" * 70)

    candidate_jamo_pointers = Counter()
    for anchor_off, anchor_val, label in composer_anchors[:50]:
        ctx_lo = anchor_off - 0x100
        ctx_hi = anchor_off + 0x100
        local_literals = []
        for off in range(ctx_lo & ~3, ctx_hi & ~3, 4):
            v = int.from_bytes(data[off:off + 4], "little")
            if PATCHED_LO <= v < PATCHED_HI:
                local_literals.append((off, v))
                candidate_jamo_pointers[v] += 1

        if local_literals:
            print(f"\nanchor {anchor_off:#x} ({label}) -> EWRAM {anchor_val:#x}")
            print(f"  patched-ROM literals nearby:")
            for off, v in local_literals[:8]:
                # Inspect the bytes at the target — is it font-like?
                target = v - GBA_BASE
                if 0 <= target < len(data) - 32:
                    sample = data[target:target+16]
                    nz = sum(1 for b in sample if b != 0)
                    print(f"    @ {off:#x}: -> {v:#x} (file {target:#x})  "
                          f"first 16B: {sample.hex()} (nz={nz}/16)")

    print("\n" + "=" * 70)
    print(f"Top jamo-atlas candidates (patched-region pointers reused near composer anchors):")
    print("=" * 70)
    for v, c in candidate_jamo_pointers.most_common(20):
        target = v - GBA_BASE
        sample = data[target:target+16]
        nz = sum(1 for b in sample if b != 0)
        print(f"  {v:#x} (file {target:#x}): reused {c}×  first16: {sample.hex()} (nz={nz})")


if __name__ == "__main__":
    main()
