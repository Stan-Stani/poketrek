#!/usr/bin/env python3
"""Triangulate the 16-bit codepoint -> hangul-syllable mapping used by the
2024 patched ROM's gMoveNames/gAbilityNames/gSpeciesNames tables.

Inputs:
  - ROM bytes for the three tables
  - Canonical (Korean) names from PokeAPI CSVs

Output:
  - codepoint_map.json: { "<be16-hex>": "<hangul char>" }
  - mismatches.json: entries we couldn't reconcile (typically because the
    canonical PokeAPI name doesn't match what the patch authors used; e.g.
    Pound = "막치기" in PokeAPI but maybe "치기" or "후려치기" in the patch)
"""
from __future__ import annotations
import json
from collections import Counter, defaultdict
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


def read_entry_codepoints(rom: bytes, off: int, max_len: int) -> list[int]:
    """Each codepoint is 2 BE bytes, stream until 0xFF terminator."""
    out = []
    i = 0
    while i < max_len:
        b = rom[off + i]
        if b == 0xFF:
            break
        # Each codepoint is 2 bytes
        if i + 1 >= max_len:
            break
        hi = b
        lo = rom[off + i + 1]
        cp = (hi << 8) | lo
        out.append(cp)
        i += 2
    return out


def build_table(rom: bytes, start: int, stride: int, n: int):
    """Returns list of (idx, codepoints) for entries with content."""
    out = []
    for i in range(n):
        cps = read_entry_codepoints(rom, start + i * stride, stride)
        out.append((i, cps))
    return out


def triangulate(name_table_label: str, entries, korean_names: dict[int, dict]):
    """For each entry, if PokeAPI gives a Korean name with the same syllable
    count as the codepoint count, vote each (codepoint, syllable) pairing.

    Returns:
      cp_to_syl: {codepoint: {syllable: count}}
      length_mismatches: list of (idx, ko, n_cps)
    """
    cp_to_syl: dict[int, Counter] = defaultdict(Counter)
    length_mismatches = []
    skipped = []
    for idx, cps in entries:
        # Pokemon ids are 1-indexed; entry 0 in tables is "?????" / "-"
        if idx == 0:
            continue
        ko_data = korean_names.get(idx)
        if not ko_data or "ko" not in ko_data:
            skipped.append((idx, None))
            continue
        ko = ko_data["ko"]
        if len(cps) != len(ko):
            length_mismatches.append((idx, ko, cps))
            continue
        for cp, syl in zip(cps, ko):
            cp_to_syl[cp][syl] += 1
    return cp_to_syl, length_mismatches, skipped


def main():
    rom = ROM.read_bytes()
    species_ko = {int(k): v for k, v in json.loads(
        (NAMES_DIR / "korean_species_names.json").read_text()).items()}
    moves_ko = {int(k): v for k, v in json.loads(
        (NAMES_DIR / "korean_move_names.json").read_text()).items()}
    abilities_ko = {int(k): v for k, v in json.loads(
        (NAMES_DIR / "korean_ability_names.json").read_text()).items()}

    # Build entries
    spec_entries = build_table(rom, GSPECIES_NAMES, GSPECIES_NAMES_STRIDE,
                               GSPECIES_NAMES_N)
    move_entries = build_table(rom, GMOVE_NAMES, GMOVE_NAMES_STRIDE,
                               GMOVE_NAMES_N)
    abil_entries = build_table(rom, GABILITY_NAMES, GABILITY_NAMES_STRIDE,
                               GABILITY_NAMES_N)

    cp_to_syl: dict[int, Counter] = defaultdict(Counter)

    # Species first — most reliable matches because pokemon names are well-
    # established Korean translations and stable.
    for table_label, entries, name_dict in [
        ("species", spec_entries, species_ko),
        ("moves", move_entries, moves_ko),
        ("abilities", abil_entries, abilities_ko),
    ]:
        partial_cp, lm, sk = triangulate(table_label, entries, name_dict)
        for cp, ctr in partial_cp.items():
            cp_to_syl[cp].update(ctr)
        n_match = sum(1 for i, _ in entries if i > 0 and i in name_dict
                      and len(read_entry_codepoints(rom, 0, 0)) is not None)
        n_align = len(entries) - len(lm) - len(sk) - 1  # minus idx 0
        print(f"  {table_label}: {n_align}/{len(entries)} entries length-aligned, "
              f"{len(lm)} length-mismatches, {len(sk)} skipped (no PokeAPI name)")

    # Resolve cp -> syllable: pick majority vote.
    resolved = {}
    ambiguous = {}
    for cp, ctr in cp_to_syl.items():
        if not ctr:
            continue
        most_common = ctr.most_common()
        top_syl, top_count = most_common[0]
        if len(most_common) == 1 or top_count > most_common[1][1]:
            resolved[cp] = top_syl
        else:
            # Tie — record as ambiguous
            ambiguous[cp] = dict(ctr)

    print(f"\nResolved {len(resolved)} codepoints, {len(ambiguous)} ambiguous")

    # Save
    (NAMES_DIR / "codepoint_map.json").write_text(
        json.dumps({f"{cp:04X}": syl for cp, syl in sorted(resolved.items())},
                   ensure_ascii=False, indent=1))
    (NAMES_DIR / "codepoint_ambiguous.json").write_text(
        json.dumps({f"{cp:04X}": v for cp, v in sorted(ambiguous.items())},
                   ensure_ascii=False, indent=1))

    # Now decode all entries using the resolved map and find which are
    # length-mismatches we can investigate further.
    def decode(cps):
        return "".join(resolved.get(cp, f"<{cp:04X}>") for cp in cps)

    print("\n=== Sample decoded ===")
    print("species:")
    for i in [1, 4, 7, 25, 150, 386]:
        cps = next(c for idx, c in spec_entries if idx == i)
        print(f"  {i}: {decode(cps)}  (PokeAPI ko: {species_ko.get(i, {}).get('ko')!r})")
    print("\nmoves:")
    for i in [1, 33, 56, 91, 156]:
        cps = next(c for idx, c in move_entries if idx == i)
        print(f"  {i}: {decode(cps)}  (PokeAPI ko: {moves_ko.get(i, {}).get('ko')!r})")
    print("\nabilities:")
    for i in [1, 22, 65]:
        cps = next(c for idx, c in abil_entries if idx == i)
        print(f"  {i}: {decode(cps)}  (PokeAPI ko: {abilities_ko.get(i, {}).get('ko')!r})")


if __name__ == "__main__":
    main()
