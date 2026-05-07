#!/usr/bin/env python3
"""Decode all entries in gMoveNames/gAbilityNames/gSpeciesNames using the
current codepoint_map.json. Report unresolved codepoints and partial decodes.
"""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ROM = ROOT / "tools/moneo/rom_swap/leafgreen_J-K_2024.gba"
NAMES_DIR = Path(__file__).resolve().parent

GMOVE_NAMES = 0x2470E0
GMOVE_NAMES_STRIDE = 13
GMOVE_NAMES_N = 355

GABILITY_NAMES = 0x24FC8C
GABILITY_NAMES_STRIDE = 13
GABILITY_NAMES_N = 78

GSPECIES_NAMES = 0x245F2C
GSPECIES_NAMES_STRIDE = 11
GSPECIES_NAMES_N = 412


def read_codepoints(rom: bytes, off: int, max_len: int) -> list[int]:
    out = []
    i = 0
    while i < max_len:
        b = rom[off + i]
        if b == 0xFF:
            break
        if i + 1 >= max_len:
            break
        cp = (b << 8) | rom[off + i + 1]
        out.append(cp)
        i += 2
    return out


def main():
    rom = ROM.read_bytes()
    cp_map = {int(k, 16): v for k, v in
              json.loads((NAMES_DIR / "codepoint_map.json").read_text()).items()}

    unresolved = Counter()
    decoded_each = {"moves": [], "abilities": [], "species": []}

    for label, start, stride, n in [
        ("moves", GMOVE_NAMES, GMOVE_NAMES_STRIDE, GMOVE_NAMES_N),
        ("abilities", GABILITY_NAMES, GABILITY_NAMES_STRIDE, GABILITY_NAMES_N),
        ("species", GSPECIES_NAMES, GSPECIES_NAMES_STRIDE, GSPECIES_NAMES_N),
    ]:
        clean = 0
        partial = 0
        empty = 0
        for i in range(n):
            cps = read_codepoints(rom, start + i * stride, stride)
            if not cps or all(cp in (0xFFFF, 0xACAC, 0xACFF, 0xAEAE) for cp in cps):
                empty += 1
                decoded_each[label].append((i, ""))
                continue
            decoded = []
            unres_here = 0
            for cp in cps:
                ch = cp_map.get(cp)
                if ch:
                    decoded.append(ch)
                else:
                    decoded.append(f"<{cp:04X}>")
                    unresolved[cp] += 1
                    unres_here += 1
            text = "".join(decoded)
            decoded_each[label].append((i, text))
            if unres_here == 0:
                clean += 1
            else:
                partial += 1
        print(f"{label}: clean={clean}/{n}  partial={partial}  empty/placeholder={empty}")

    print(f"\nTop 30 unresolved codepoints:")
    for cp, count in unresolved.most_common(30):
        print(f"  {cp:04X}: appears in {count} positions")
    print(f"\nTotal unresolved codepoints: {len(unresolved)}")
    print(f"Total positions affected: {sum(unresolved.values())}")

    # Save
    (NAMES_DIR / "decoded_names.json").write_text(
        json.dumps(decoded_each, ensure_ascii=False, indent=1))
    print(f"\nSaved -> {NAMES_DIR / 'decoded_names.json'}")


if __name__ == "__main__":
    main()
