#!/usr/bin/env python3
"""Locate gMoveNames, gAbilityNames, gSpeciesNames in the 2024 patched ROM.

Strategy: name tables are inline byte arrays (NOT pointer tables) with fixed
stride. Each entry is a FF-terminated string of glyph bytes. We search for
runs of plausible glyph bytes at the given stride.

A name byte is "plausible" if it's:
  - 0xFF (terminator)
  - 0xF0..0xF6 (page-prefix)
  - 0x00..0xEF (single-byte glyph or page-suffix; alphanumeric/space etc)
"""
from __future__ import annotations
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ROM = ROOT / "tools/moneo/rom_swap/leafgreen_J-K_2024.gba"

# Canonical FRLG counts
N_MOVES = 355  # MOVES_COUNT in pokefirered
N_ABILITIES = 78
N_SPECIES = 412  # NUM_SPECIES; gSpeciesNames sized to NUM_SPECIES from species.h


def is_glyph_byte(b: int) -> bool:
    # Anything except a "block" of zeros or random pointer-bytes.
    # Allow 0..0xFF really; we check structure separately.
    return True


def looks_like_name_entry(rom: bytes, off: int, stride: int) -> bool:
    """A name entry is FF-terminated within `stride` bytes, with at least 1
    non-FF byte before the FF, and no NUL bytes (NULs only valid in pointer
    tables which interleave name strings if at all)."""
    if off + stride > len(rom):
        return False
    chunk = rom[off:off + stride]
    # Find first FF
    if 0xFF not in chunk:
        return False
    ff_idx = chunk.index(0xFF)
    if ff_idx == 0:
        return False
    # No NUL before FF
    if 0x00 in chunk[:ff_idx]:
        return False
    return True


def score_table(rom: bytes, off: int, stride: int, n_entries: int) -> int:
    """How many of the first n_entries entries look like name strings?"""
    good = 0
    for i in range(n_entries):
        if looks_like_name_entry(rom, off + i * stride, stride):
            good += 1
    return good


def find_table(rom: bytes, stride: int, n_entries: int, label: str,
               start: int = 0x100000, end: int = 0x800000):
    """Search aligned 1-byte for a long run of name-like entries."""
    print(f"\n=== Searching for {label} (stride={stride}, n={n_entries}) ===")
    best = []
    # Step by 1 (tables aren't necessarily 4-aligned; they're byte arrays)
    # but most tables in pokefirered are 4-aligned data.
    threshold = int(n_entries * 0.95)
    for off in range(start, min(end, len(rom)) - n_entries * stride, 4):
        # Quick early-out: first 5 entries should look like names
        ok = True
        for i in range(5):
            if not looks_like_name_entry(rom, off + i * stride, stride):
                ok = False
                break
        if not ok:
            continue
        score = score_table(rom, off, stride, n_entries)
        if score >= threshold:
            best.append((score, off))
    best.sort(reverse=True)
    for score, off in best[:5]:
        print(f"  off=0x{off:X}  score={score}/{n_entries}")
    return best


def main():
    rom = ROM.read_bytes()
    print(f"ROM: {len(rom):,} bytes")

    find_table(rom, 13, N_MOVES, "gMoveNames")
    find_table(rom, 13, N_ABILITIES, "gAbilityNames")
    find_table(rom, 11, N_SPECIES, "gSpeciesNames")


if __name__ == "__main__":
    main()
