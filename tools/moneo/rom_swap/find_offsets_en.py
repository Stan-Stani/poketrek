#!/usr/bin/env python3
"""Verify the canonical name-table offsets in the English LeafGreen ROM.

Anchors:
  gSpeciesNames[1] = "BULBASAUR"
  gMoveNames[1]    = "POUND"
  gAbilityNames[1] = "STENCH"
  gItems[1]        = "MASTER BALL"
  gPokedex[1].cat  = "SEED"

If any anchor disagrees with the constants in `rom_config_en.py`, the
script exits non-zero so CI / the runbook can catch a re-spun ROM before
the gloss pipeline silently emits garbage.
"""
from __future__ import annotations
import sys
import zlib
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent))
from rom_config_en import (  # noqa: E402
    ROM_PATH_EN, ROM_CRC32_EN,
    GMOVE_NAMES_EN, GMOVE_NAMES_EN_STRIDE,
    GABILITY_NAMES_EN, GABILITY_NAMES_EN_STRIDE,
    GSPECIES_NAMES_EN, GSPECIES_NAMES_EN_STRIDE,
    GITEMS_EN, GITEMS_EN_STRIDE, GITEMS_EN_NAME_OFF,
    GPOKEDEX_ENTRIES_EN, GPOKEDEX_EN_STRIDE, GPOKEDEX_EN_CATEGORY_OFF,
    EN_CHARMAP, EN_END_MARKER, EN_NEWLINE_BYTES, EN_INLINE_PREFIXES_WITH_ARG,
)


def decode(rom: bytes, off: int, n: int) -> str:
    out: list[str] = []
    for i in range(n):
        b = rom[off + i]
        if b == EN_END_MARKER: break
        out.append(EN_CHARMAP.get(b, f"\\x{b:02X}"))
    return "".join(out)


def main() -> int:
    rom = ROM_PATH_EN.read_bytes()
    crc = zlib.crc32(rom)
    if crc != ROM_CRC32_EN:
        print(f"FAIL: ROM CRC mismatch: got 0x{crc:08X}, want 0x{ROM_CRC32_EN:08X}")
        return 1

    checks = [
        ("gSpeciesNames[1]", GSPECIES_NAMES_EN + GSPECIES_NAMES_EN_STRIDE, 11, "BULBASAUR"),
        ("gMoveNames[1]",    GMOVE_NAMES_EN + GMOVE_NAMES_EN_STRIDE, 13, "POUND"),
        ("gAbilityNames[1]", GABILITY_NAMES_EN + GABILITY_NAMES_EN_STRIDE, 13, "STENCH"),
        ("gItems[1].name",   GITEMS_EN + GITEMS_EN_STRIDE + GITEMS_EN_NAME_OFF, 14, "MASTER BALL"),
        ("gPokedex[1].cat",  GPOKEDEX_ENTRIES_EN + GPOKEDEX_EN_STRIDE + GPOKEDEX_EN_CATEGORY_OFF, 12, "SEED"),
    ]
    ok = True
    for label, off, n, want in checks:
        got = decode(rom, off, n)
        flag = "OK" if got == want else "FAIL"
        if got != want: ok = False
        print(f"  [{flag}] {label} @ 0x{off:06X}  got={got!r:14s} want={want!r}")

    if ok:
        print("All anchors match.")
        return 0
    print("Anchors disagree — update rom_config_en.py before running the pipeline.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
