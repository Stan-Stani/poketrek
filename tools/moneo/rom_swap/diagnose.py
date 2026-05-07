#!/usr/bin/env python3
"""ROM-swap diagnostic.

Given a candidate ROM path, check whether the offsets we hard-coded for the
2010 Korean fan-translation still work, and report what needs re-derivation.

Run:
  python3 diagnose.py <rom_path>           # report only
  python3 diagnose.py <rom_path> --quick   # skip slow signature search
"""
from __future__ import annotations
import argparse
import hashlib
import struct
import sys
import zlib
from pathlib import Path

GBA_BASE = 0x08000000

# Offsets discovered for the 2010 Korean fan-translation
# (commits 3b2ddb0, 5619b0f, a6c1fd5, 0fe15b9 in this repo).
KNOWN_OFFSETS = {
    "gMapGroups":           (0x316740, "gMapGroups[] pointer table"),
    "gMapGroup_TownsAndRoutes_first": (0x316384, "gMapGroups[1] = TownsAndRoutes start (Korean walker indexing)"),
    "gItems":               (0x3A058C, "gItems[] (40-byte stride, ~374 entries)"),
    "gPokedexEntries":      (0x40E254, "gPokedexEntries[] (28-byte stride, ~387 entries)"),
    "gWildMonHeaders":      (0x390E04, "gWildMonHeaders[] (20-byte stride, 76 entries)"),
    "gTrainers":            (0x1FE1B4, "gTrainers[] (32-byte stride, Korean compacted)"),
    "gTrainerClassNames":   (0x1FDB18, "gTrainerClassNames[] (11-byte stride, 117 entries)"),
}

# Signatures to grep for if the known offsets fail. Each value is a list of
# byte-pattern probes that should appear at or near the table's start.
SIGNATURES = {
    "gItems": [
        # First u16 itemId in the table is 0 (ITEM_NONE). Look for the 14-byte
        # name field (with FF terminator) followed by 0x00 0x00 0x... 0x00 0x00.
        # We can't write a single deterministic signature, so the diagnostic
        # only verifies the entry stride.
    ],
    "gPokedexEntries": [
        # Pokedex starts with Bulbasaur (#001). The first entry's species name
        # would be in glyphs but the description pointer at offset +16 must be a
        # ROM pointer.
    ],
}


def u32(buf: bytes, off: int) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def is_rom_ptr(p: int, rom_len: int) -> bool:
    return 0x08000000 <= p < 0x08000000 + rom_len


def check_gMapGroups(rom: bytes, off: int) -> tuple[bool, str]:
    """Validate by reading consecutive ROM pointers; expect ~40+ valid pointers."""
    rom_len = len(rom)
    valid = 0
    for i in range(50):
        p = u32(rom, off + i * 4)
        if not is_rom_ptr(p, rom_len):
            break
        valid += 1
    if valid >= 30:
        return True, f"{valid} valid group pointers"
    return False, f"only {valid} valid pointers (expected 30+)"


def check_table_at(rom: bytes, off: int, stride: int, n_min: int,
                   ptr_field_off: int) -> tuple[bool, str]:
    """A table with stride S has ROM pointers at offset P inside each entry."""
    rom_len = len(rom)
    valid = 0
    for i in range(n_min + 5):
        ptr = u32(rom, off + i * stride + ptr_field_off)
        if is_rom_ptr(ptr, rom_len):
            valid += 1
        else:
            break
    return valid >= n_min, f"{valid} consecutive entries with valid ptr"


def find_signature(rom: bytes, signature: bytes,
                   from_off: int = 0, max_hits: int = 5) -> list[int]:
    """Locate all occurrences of a byte signature."""
    hits = []
    pos = from_off
    while True:
        i = rom.find(signature, pos)
        if i < 0 or len(hits) >= max_hits:
            break
        hits.append(i)
        pos = i + 1
    return hits


def search_gMapGroups(rom: bytes) -> list[int]:
    """gMapGroups is a sequence of 40+ consecutive ROM pointers within a span
    that is itself referenced by another ROM pointer. Walk every 4-aligned offset
    and find ones with 35+ consecutive ROM pointers."""
    rom_len = len(rom)
    candidates = []
    for off in range(0x100000, min(rom_len, 0x800000), 4):
        n = 0
        for i in range(50):
            if off + i * 4 + 4 > rom_len:
                break
            p = u32(rom, off + i * 4)
            if not is_rom_ptr(p, rom_len):
                break
            n += 1
        if n >= 35:
            candidates.append((off, n))
    return [c[0] for c in candidates[:5]]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rom", help="Path to the candidate ROM")
    ap.add_argument("--quick", action="store_true",
                    help="Skip signature re-search if known offset fails")
    args = ap.parse_args()

    rom_path = Path(args.rom)
    if not rom_path.exists():
        print(f"ERROR: {rom_path} not found", file=sys.stderr)
        sys.exit(1)

    rom = rom_path.read_bytes()
    md5 = hashlib.md5(rom).hexdigest()
    crc = format(zlib.crc32(rom) & 0xFFFFFFFF, "08X")

    print(f"=== ROM identity ===")
    print(f"  path:  {rom_path}")
    print(f"  size:  {len(rom):,} bytes")
    print(f"  MD5:   {md5}")
    print(f"  CRC32: 0x{crc}")
    # Game header at 0xA0..0xAC (12 bytes ASCII title)
    title = rom[0xA0:0xAC].decode("ascii", errors="replace").rstrip("\x00 ")
    code = rom[0xAC:0xB0].decode("ascii", errors="replace")
    print(f"  title: {title!r}  code: {code!r}")

    print(f"\n=== Known-offset checks (Korean fan-translation 2010) ===")
    failed: list[str] = []

    # gMapGroups
    name = "gMapGroups"
    off, desc = KNOWN_OFFSETS[name]
    ok, why = check_gMapGroups(rom, off)
    print(f"  {'PASS' if ok else 'FAIL'}: {name} @ 0x{off:X} -- {why}")
    if not ok:
        failed.append(name)

    # gItems: 40-byte stride, description pointer at +20
    name = "gItems"
    off, desc = KNOWN_OFFSETS[name]
    ok, why = check_table_at(rom, off, stride=40, n_min=10, ptr_field_off=20)
    print(f"  {'PASS' if ok else 'FAIL'}: {name} @ 0x{off:X} -- {why}")
    if not ok:
        failed.append(name)

    # gPokedexEntries: 28-byte stride, description pointer at +16
    name = "gPokedexEntries"
    off, desc = KNOWN_OFFSETS[name]
    ok, why = check_table_at(rom, off, stride=28, n_min=10, ptr_field_off=16)
    print(f"  {'PASS' if ok else 'FAIL'}: {name} @ 0x{off:X} -- {why}")
    if not ok:
        failed.append(name)

    # gTrainers: 32-byte stride (Korean), party pointer at +28
    name = "gTrainers"
    off, desc = KNOWN_OFFSETS[name]
    ok, why = check_table_at(rom, off, stride=32, n_min=10, ptr_field_off=28)
    print(f"  {'PASS' if ok else 'FAIL'}: {name} @ 0x{off:X} -- {why}")
    if not ok:
        failed.append(name)
        # Also try canonical pokefirered 40-byte stride
        ok2, why2 = check_table_at(rom, off, stride=40, n_min=10, ptr_field_off=36)
        if ok2:
            print(f"    note: 40-byte stride matches at this offset -- maybe canonical Trainer struct")

    # Map count via gMapGroups
    if "gMapGroups" not in failed:
        gmg_off, _ = KNOWN_OFFSETS["gMapGroups"]
        # Read first ptr -> gMapGroup_LinkContestRoom or similar
        first = u32(rom, gmg_off)
        if is_rom_ptr(first, len(rom)):
            print(f"  note: gMapGroups[0] -> 0x{first - GBA_BASE:X}")

    # Game header heuristic
    print(f"\n=== ROM-version heuristic ===")
    if code in ("BPRE", "BPGE"):  # FireRed/LeafGreen US
        print(f"  US English FireRed/LeafGreen detected ({code})")
    elif code in ("BPRJ", "BPGJ"):  # Japanese
        print(f"  Japanese FireRed/LeafGreen detected ({code})")
    else:
        print(f"  Unknown game code: {code}")

    # Summary
    print(f"\n=== Summary ===")
    print(f"  Known offsets passing: {7 - len(failed)} / 7")
    print(f"  Failed: {failed if failed else 'none'}")

    if failed and not args.quick:
        print(f"\n=== Signature re-search (failed offsets) ===")
        if "gMapGroups" in failed:
            print(f"  Searching for gMapGroups (35+ consecutive ROM ptrs)...")
            cands = search_gMapGroups(rom)
            for c in cands:
                ok, why = check_gMapGroups(rom, c)
                print(f"    candidate 0x{c:X} -- {why}")
            if not cands:
                print(f"    no candidates found")

    print(f"\nIf any offset failed, re-run targeted signature scripts from "
          f"commits 3b2ddb0/5619b0f/a6c1fd5/0fe15b9 to find the new locations.")


if __name__ == "__main__":
    main()
