#!/usr/bin/env python3
"""Decode the located name tables in the 2024 patched ROM and verify against
canonical pokefirered indices.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ROM = ROOT / "tools/moneo/rom_swap/leafgreen_J-K_2024.gba"
GLYPH_MAP = ROOT / "tools/moneo/glyph-map.json"

GMOVE_NAMES = 0x2470E0
GMOVE_NAMES_STRIDE = 13
GMOVE_NAMES_N = 355

GABILITY_NAMES = 0x24FC8C
GABILITY_NAMES_STRIDE = 13
GABILITY_NAMES_N = 78

GSPECIES_NAMES = 0x245F2C
GSPECIES_NAMES_STRIDE = 11
GSPECIES_NAMES_N = 412


def build_decoder(glyph_map: dict[str, str]) -> dict:
    """Returns a structure for decoding: page0 single-byte map +
    pageN two-byte map."""
    page0 = {}    # idx -> char
    pages = {}    # (page, idx) -> char
    for k, ch in glyph_map.items():
        if not ch or "," not in k:
            continue
        page_str, idx_str = k.split(",", 1)
        page = int(page_str[1:])  # "F3" -> 3
        idx = int(idx_str)
        if page == 0:
            page0[idx] = ch
        else:
            pages[(page, idx)] = ch
    return {"page0": page0, "pages": pages}


def decode_entry(rom: bytes, off: int, max_len: int, decoder: dict) -> tuple[str, int]:
    """Decode a FF-terminated name entry. Returns (text, byte_length)."""
    out = []
    page0 = decoder["page0"]
    pages = decoder["pages"]
    i = 0
    raw_bytes = []
    while i < max_len:
        b = rom[off + i]
        if b == 0xFF:
            break
        raw_bytes.append(b)
        if 0xF1 <= b <= 0xF6:
            page = b - 0xF0
            if i + 1 >= max_len:
                out.append(f"<{b:02X}>")
                break
            idx = rom[off + i + 1]
            ch = pages.get((page, idx))
            if ch:
                out.append(ch)
            else:
                out.append(f"<{b:02X},{idx:02X}>")
            i += 2
        else:
            ch = page0.get(b)
            if ch:
                out.append(ch)
            else:
                out.append(f"<{b:02X}>")
            i += 1
    return "".join(out), i


def main():
    rom = ROM.read_bytes()
    glyph_map = json.loads(GLYPH_MAP.read_text())["map"]
    decoder = build_decoder(glyph_map)

    print("=== gMoveNames ===")
    print("idx | decoded")
    for idx in [0, 1, 2, 33, 52, 53, 56, 58, 91, 156, 157]:
        off = GMOVE_NAMES + idx * GMOVE_NAMES_STRIDE
        text, _ = decode_entry(rom, off, GMOVE_NAMES_STRIDE, decoder)
        print(f"  {idx:3d} | {text!r}")

    print("\n=== gAbilityNames ===")
    for idx in [0, 1, 2, 5, 9, 22, 65, 76]:
        off = GABILITY_NAMES + idx * GABILITY_NAMES_STRIDE
        text, _ = decode_entry(rom, off, GABILITY_NAMES_STRIDE, decoder)
        print(f"  {idx:3d} | {text!r}")

    print("\n=== gSpeciesNames ===")
    for idx in [0, 1, 4, 7, 25, 150, 151, 248, 386]:
        off = GSPECIES_NAMES + idx * GSPECIES_NAMES_STRIDE
        text, _ = decode_entry(rom, off, GSPECIES_NAMES_STRIDE, decoder)
        print(f"  {idx:3d} | {text!r}")


if __name__ == "__main__":
    main()
