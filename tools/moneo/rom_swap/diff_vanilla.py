#!/usr/bin/env python3
"""Diff the 2024 Korean LeafGreen ROM against the vanilla Japanese base.

Goal: locate every byte-range the patch modified inside the vanilla code
region (< 0x800000). Those are the rewritten functions — the Korean
text/glyph rendering is one of them. Group consecutive changed bytes into
"runs" so we can quickly inspect the largest patches.
"""
from __future__ import annotations
from pathlib import Path

VANILLA = Path("/Users/isolate/Developer/poketrek/1362 - Pokemon Leaf Green (J)(Cezar).gba")
KOR_2024 = Path("/Users/isolate/Developer/poketrek/tools/moneo/rom_swap/leafgreen_J-K_2024.gba")
OUT_RUNS = Path("/Users/isolate/Developer/poketrek/tools/moneo/rom_swap/diff_runs_2024.txt")


def main():
    a = VANILLA.read_bytes()
    b = KOR_2024.read_bytes()
    n = min(len(a), len(b))
    print(f"Vanilla: {len(a):#x} bytes")
    print(f"2024 KO: {len(b):#x} bytes")
    print(f"Comparing first {n:#x} bytes")

    # Find runs of differences with at most GAP unchanged bytes between them.
    GAP = 8
    runs = []
    i = 0
    while i < n:
        if a[i] != b[i]:
            start = i
            last_diff = i
            i += 1
            while i < n:
                if a[i] != b[i]:
                    last_diff = i
                    i += 1
                else:
                    if i - last_diff > GAP:
                        break
                    i += 1
            runs.append((start, last_diff + 1))
        else:
            i += 1

    print(f"\nFound {len(runs)} difference runs (≤{GAP}-byte gaps merged)")

    # Bucket by region
    by_region = {"vanilla_code": [], "between": [], "patched": []}
    for start, end in runs:
        if start < 0x800000:
            by_region["vanilla_code"].append((start, end))
        elif start < 0xD00000:
            by_region["between"].append((start, end))
        else:
            by_region["patched"].append((start, end))

    for region, items in by_region.items():
        total = sum(e - s for s, e in items)
        print(f"  {region}: {len(items)} runs, {total} bytes")

    # Largest runs in vanilla code region — those are the rewritten functions.
    code_runs = sorted(by_region["vanilla_code"], key=lambda r: -(r[1] - r[0]))
    print(f"\n=== Top 30 longest patches in vanilla code region (< 0x800000) ===")
    print(f"{'rank':>4}  {'start':>10}  {'end':>10}  {'len':>6}  context")
    for i, (s, e) in enumerate(code_runs[:30]):
        # Show 32 bytes from each side
        print(f"{i+1:>4}  {s:>10x}  {e:>10x}  {e-s:>6}  vanilla={a[s:s+8].hex()} → kor={b[s:s+8].hex()}")

    OUT_RUNS.write_text("\n".join(
        f"{s:08x}\t{e:08x}\t{e-s}\t{a[s:s+16].hex()}\t{b[s:s+16].hex()}"
        for s, e in by_region["vanilla_code"]
    ))
    print(f"\nFull vanilla-code diff list → {OUT_RUNS}")


if __name__ == "__main__":
    main()
