#!/usr/bin/env python3
"""For every 32-byte tile in the VRAM dump, search the ROM for that exact
sequence. Tiles that match in the patched region (≥ 0xD00000) and have
glyph-like density are font tile candidates. Cluster matches by source
offset to find the font_base (the offset where many consecutive VRAM
tiles map to consecutive ROM bytes).
"""
from __future__ import annotations
from pathlib import Path
from collections import defaultdict, Counter

VRAM_DUMP = Path("/tmp/vram_at_title.bin")
ROM = Path(__file__).resolve().parent / "leafgreen_J-K_2024.gba"


def main():
    vram = VRAM_DUMP.read_bytes()
    rom = ROM.read_bytes()

    # Step 1: enumerate VRAM tiles that look like character glyphs (not all-zero, not all-fill).
    candidate_tiles: list[tuple[int, bytes]] = []  # (vram_off, tile_bytes)
    for off in range(0, len(vram) - 32, 32):
        tile = vram[off:off+32]
        nonzero = sum(1 for b in tile if b != 0)
        # Skip blank tiles and solid-fill tiles
        if nonzero < 4 or nonzero > 30:
            continue
        candidate_tiles.append((off, tile))

    print(f"Found {len(candidate_tiles)} non-blank VRAM tiles to search for")

    # Step 2: build a small index of unique tiles
    seen = {}
    for off, tile in candidate_tiles:
        seen.setdefault(tile, []).append(off)
    print(f"Unique non-blank tiles: {len(seen)}")

    # Step 3: for each unique tile, find ALL occurrences in ROM
    print("\nSearching ROM for each unique VRAM tile (this may take a while)...")
    tile_to_rom_offsets: dict[bytes, list[int]] = {}
    progress = 0
    for tile in seen:
        progress += 1
        if progress % 50 == 0:
            print(f"  {progress}/{len(seen)}")
        offs = []
        i = 0
        while True:
            pos = rom.find(tile, i)
            if pos == -1:
                break
            offs.append(pos)
            i = pos + 1
        tile_to_rom_offsets[tile] = offs

    # Step 4: report per-tile match counts and locations.
    matched_in_patched = 0
    one_match_total = 0
    print("\n=== Per-tile ROM-match summary ===")
    print(f"{'vram_off':>8} {'rom_hits':>8} {'first':>10} {'last':>10}  region")
    for off, tile in candidate_tiles[:50]:
        offs = tile_to_rom_offsets[tile]
        if not offs:
            continue
        if len(offs) == 1:
            one_match_total += 1
        first = offs[0]; last = offs[-1]
        in_patched = sum(1 for o in offs if o >= 0xD00000)
        if in_patched > 0:
            matched_in_patched += 1
        region = "PATCHED" if first >= 0xD00000 else "VANILLA" if first < 0x800000 else "OTHER"
        print(f"{off:>8x} {len(offs):>8} {first:>10x} {last:>10x}  {region}")

    print(f"\nTotal candidate tiles: {len(candidate_tiles)}")
    print(f"Tiles with at least one ROM hit in patched region: {matched_in_patched}")
    print(f"Tiles with exactly 1 ROM hit total: {one_match_total}")

    # Step 5: find clusters of consecutive VRAM tiles that map to a consecutive
    # ROM region — that's the font_base + offset within it.
    # For each VRAM offset, get its (first) ROM match. Look for long monotonic runs
    # where rom_off[i+1] - rom_off[i] == 32.
    vram_to_rom = []
    for off, tile in candidate_tiles:
        offs = tile_to_rom_offsets[tile]
        if offs:
            # pick the patched-region match if available
            patched = [o for o in offs if o >= 0xD00000]
            chosen = patched[0] if patched else offs[0]
            vram_to_rom.append((off, chosen))

    # Find runs of stride-32 between consecutive entries (allowing any vram delta).
    runs = []
    cur = None
    for vo, ro in vram_to_rom:
        if cur is None:
            cur = [(vo, ro)]
        else:
            prev_v, prev_r = cur[-1]
            # check if rom offset advanced by tile_size * (vram_delta / 32)
            v_delta = vo - prev_v
            r_delta = ro - prev_r
            if v_delta > 0 and r_delta == v_delta:
                cur.append((vo, ro))
            else:
                if len(cur) >= 4:
                    runs.append(cur)
                cur = [(vo, ro)]
    if cur and len(cur) >= 4:
        runs.append(cur)

    runs.sort(key=lambda r: -len(r))
    print(f"\n=== Top 10 longest VRAM↔ROM consecutive runs ===")
    print(f"{'run_len':>7} {'first_vram':>10} {'first_rom':>10} {'last_rom':>10}  region")
    for r in runs[:10]:
        v0, r0 = r[0]
        v1, r1 = r[-1]
        region = "PATCHED" if r0 >= 0xD00000 else "VANILLA" if r0 < 0x800000 else "OTHER"
        print(f"{len(r):>7} {v0:>10x} {r0:>10x} {r1:>10x}  {region}")
    if not runs:
        print("(no consecutive runs of ≥4 found)")


if __name__ == "__main__":
    main()
