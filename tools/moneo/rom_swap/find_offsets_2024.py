#!/usr/bin/env python3
"""Find new ROM offsets for the 2024-02-29 Korean patch (BPGE-canonical).

Walks the ROM looking for the canonical FRLG/BPGE table layouts and reports
candidates. Run from repo root:
    python3 tools/moneo/rom_swap/find_offsets_2024.py
"""
from __future__ import annotations
import struct
import sys
from pathlib import Path

GBA_BASE = 0x08000000
ROM_PATH = Path(__file__).resolve().parent / "leafgreen_J-K_2024.gba"


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def is_rom_ptr(p, n):
    return GBA_BASE <= p < GBA_BASE + n


def find_gMapGroups(rom):
    """Canonical FRLG has gMapGroups[] with 43 group pointers (or 42-44 depending
    on patches). Scan for runs of 35+ consecutive ROM pointers to ROM regions
    that themselves look like map-pointer tables (lots of ROM pointers).

    Filter further: the run length should be 40-50 (not 100+ -- that would be
    a different table).
    """
    n = len(rom)
    out = []
    i = 0x100000  # Korean ROM had 0x316740; canonical FRLG has 0x3526A8
    while i < min(n, 0x800000):
        # Quick: u32-aligned, valid ptr, prev not valid
        p = u32(rom, i)
        if not is_rom_ptr(p, n):
            i += 4
            continue
        prev = u32(rom, i - 4) if i >= 4 else 0
        if is_rom_ptr(prev, n):
            i += 4
            continue
        # Count run length
        run = 0
        while i + run * 4 + 4 <= n:
            q = u32(rom, i + run * 4)
            if not is_rom_ptr(q, n):
                break
            run += 1
        if 35 <= run <= 60:
            # Check that the first pointer's target also has consecutive ROM
            # pointers (i.e. it's a map header pointer table)
            p0 = p - GBA_BASE
            if p0 + 16 < n:
                inner = 0
                for j in range(20):
                    q = u32(rom, p0 + j * 4)
                    if is_rom_ptr(q, n):
                        inner += 1
                    else:
                        break
                out.append((i, run, inner))
        i += max(run * 4, 4)
    return out


def find_gItems_struct40(rom):
    """gItems: 40-byte stride. Entry 0 = ITEM_NONE (zeros for itemId).
    Entry 1 = MASTER BALL. Each entry has at offset+20 a description ROM ptr.
    Scan for offset where the +20 field is a ROM pointer for >=200 consecutive
    entries.
    """
    n = len(rom)
    out = []
    # Stride 40, search 4-aligned
    for off in range(0x100000, min(n, 0x800000), 4):
        if off + 40 * 50 > n:
            break
        valid = 0
        for i in range(50):
            ptr = u32(rom, off + i * 40 + 20)
            if is_rom_ptr(ptr, n):
                valid += 1
            else:
                break
        if valid >= 50:
            # Verify continued run length
            full = 0
            for i in range(400):
                if off + i * 40 + 24 > n:
                    break
                ptr = u32(rom, off + i * 40 + 20)
                if is_rom_ptr(ptr, n):
                    full += 1
                else:
                    break
            if full >= 200:
                out.append((off, full))
    return out


def find_gPokedexEntries(rom):
    """gPokedexEntries: 36-byte stride (canonical PokedexEntry is 0x24 = 36).
    Entry 0 = DUMMY. desc ptr at +16, unusedDescription ptr at +20.
    Both should be ROM pointers for >=300 entries.
    """
    n = len(rom)
    out = []
    for off in range(0x100000, min(n, 0x800000), 4):
        if off + 36 * 30 > n:
            break
        valid = 0
        for i in range(30):
            ptr = u32(rom, off + i * 36 + 16)
            ptr2 = u32(rom, off + i * 36 + 20)
            if is_rom_ptr(ptr, n) and is_rom_ptr(ptr2, n):
                valid += 1
            else:
                break
        if valid >= 30:
            full = 0
            for i in range(420):
                if off + i * 36 + 24 > n:
                    break
                ptr = u32(rom, off + i * 36 + 16)
                ptr2 = u32(rom, off + i * 36 + 20)
                if is_rom_ptr(ptr, n) and is_rom_ptr(ptr2, n):
                    full += 1
                else:
                    break
            if full >= 200:
                out.append((off, full))
    return out


def find_gTrainers_canonical(rom):
    """gTrainers: 40-byte (0x28) stride. partyFlags at +0 is small (0-3),
    trainerClass at +1 (0-65), encMusic at +2, picture at +3, name 12 bytes
    at +4, items 4 u16 at +0x10, doubleBattle byte at +0x18, aiFlags u32 at +0x1C,
    partySize at +0x20, party ptr at +0x24.

    Search for a 40-byte stride table where the +0x24 ptr is a ROM pointer for
    >= 200 consecutive entries AND the +0x20 partySize is reasonable (1-6).
    """
    n = len(rom)
    out = []
    for off in range(0x100000, min(n, 0x800000), 4):
        if off + 40 * 50 > n:
            break
        valid = 0
        for i in range(50):
            party_ptr = u32(rom, off + i * 40 + 36)
            party_size = rom[off + i * 40 + 32]
            partyFlags = rom[off + i * 40 + 0]
            if is_rom_ptr(party_ptr, n) and 0 <= party_size <= 6 and partyFlags < 4:
                valid += 1
            else:
                break
        if valid >= 50:
            full = 0
            for i in range(800):
                if off + i * 40 + 40 > n:
                    break
                party_ptr = u32(rom, off + i * 40 + 36)
                party_size = rom[off + i * 40 + 32]
                if is_rom_ptr(party_ptr, n) and 0 <= party_size <= 6:
                    full += 1
                else:
                    break
            if full >= 200:
                out.append((off, full))
    return out


def find_gWildMonHeaders(rom):
    """gWildMonHeaders: 20-byte stride, header (mapGroup u8, mapNum u8, pad u16,
    landMonsInfo ROM-or-NULL, waterMonsInfo ROM-or-NULL, rockMonsInfo, fishMonsInfo).
    The struct is:
        u8 mapGroup; u8 mapNum; u16 pad; const* land; const* water; const* rock; const* fish
    Total = 4 (header) + 16 (4 ptrs) = 20 bytes.

    At least one of the four ptrs is non-NULL ROM ptr per header.
    Headers terminate with mapGroup=0xFF, mapNum=0xFF.
    """
    n = len(rom)
    out = []
    for off in range(0x100000, min(n, 0x800000), 4):
        if off + 20 * 30 > n:
            break
        valid = 0
        any_ptr = 0
        for i in range(30):
            base = off + i * 20
            mg = rom[base]
            mn = rom[base + 1]
            pad_lo = rom[base + 2]
            pad_hi = rom[base + 3]
            ptrs = [u32(rom, base + 4 + j * 4) for j in range(4)]
            # Header validity: pad bytes typically 0; pointers null (0) or ROM
            ok = (pad_lo, pad_hi) == (0, 0) and mg < 50 and mn < 200
            ptrs_valid = all(p == 0 or is_rom_ptr(p, n) for p in ptrs)
            has_ptr = any(p != 0 and is_rom_ptr(p, n) for p in ptrs)
            if ok and ptrs_valid and has_ptr:
                valid += 1
                any_ptr += 1
            else:
                break
        if valid >= 30:
            full = 0
            for i in range(200):
                base = off + i * 20
                if base + 20 > n:
                    break
                mg = rom[base]
                mn = rom[base + 1]
                pad_lo = rom[base + 2]
                pad_hi = rom[base + 3]
                if mg == 0xFF and mn == 0xFF:
                    break
                ptrs = [u32(rom, base + 4 + j * 4) for j in range(4)]
                ok = (pad_lo, pad_hi) == (0, 0) and mg < 50 and mn < 200
                ptrs_valid = all(p == 0 or is_rom_ptr(p, n) for p in ptrs)
                has_ptr = any(p != 0 and is_rom_ptr(p, n) for p in ptrs)
                if ok and ptrs_valid and has_ptr:
                    full += 1
                else:
                    break
            if full >= 60:
                out.append((off, full))
    return out


def find_gTrainerClassNames(rom):
    """gTrainerClassNames: 13-byte stride canonical FRLG, ~107 entries.
    Each entry is up to 12 chars terminated by 0xFF, padded to 13 bytes.
    Korean ROM should have Korean glyphs (page-0 + page F1-F6 markers), so
    the actual byte distribution is non-ASCII.

    Heuristic: find a 13-byte aligned region where each row has an 0xFF byte
    somewhere in cols 0-12 and the row never starts with 0xFF (empty entries
    are just FF FF FF...).
    """
    n = len(rom)
    out = []
    for off in range(0x100000, min(n, 0x800000), 1):
        if off + 13 * 100 > n:
            break
        valid = 0
        for i in range(100):
            row = rom[off + i * 13: off + i * 13 + 13]
            if row.count(0xFF) > 11:
                break
            if 0xFF not in row:
                break
            # First byte not FF
            if row[0] == 0xFF:
                break
            valid += 1
        if valid >= 95:
            out.append((off, valid))
    return out


def main():
    rom = ROM_PATH.read_bytes()
    print(f"ROM: {ROM_PATH} ({len(rom):,} bytes)")
    print(f"Game code: {rom[0xAC:0xB0].decode()!r}")
    print()

    print("=== gItems (40-byte stride, desc@+20) ===")
    for off, n in find_gItems_struct40(rom):
        print(f"  0x{off:X}  ({n} entries)")
    print()

    print("=== gMapGroups (35-60 ROM ptr run) ===")
    for off, run, inner in find_gMapGroups(rom):
        print(f"  0x{off:X}  ({run} ptrs, first target has {inner} ROM ptrs)")
    print()

    print("=== gPokedexEntries (36-byte stride, desc+unused both ROM) ===")
    for off, n in find_gPokedexEntries(rom):
        print(f"  0x{off:X}  ({n} entries)")
    print()

    print("=== gTrainers (40-byte canonical, party@+0x24) ===")
    for off, n in find_gTrainers_canonical(rom):
        print(f"  0x{off:X}  ({n} entries)")
    print()

    print("=== gWildMonHeaders (20-byte stride) ===")
    for off, n in find_gWildMonHeaders(rom):
        print(f"  0x{off:X}  ({n} entries)")
    print()

    print("=== gTrainerClassNames (13-byte stride, ~107 entries) ===")
    for off, n in find_gTrainerClassNames(rom)[:10]:
        print(f"  0x{off:X}  ({n} entries)")


if __name__ == "__main__":
    main()
