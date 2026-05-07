#!/usr/bin/env python3
"""Iteratively resolve more codepoints by going through PokeAPI canonical
names and back-filling cps where N-1 of N codepoints are already known.

Then fall back to a hand-curated table for the few remaining ambiguities.
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
    species_ko = {int(k): v for k, v in json.loads(
        (NAMES_DIR / "korean_species_names.json").read_text()).items()}
    moves_ko = {int(k): v for k, v in json.loads(
        (NAMES_DIR / "korean_move_names.json").read_text()).items()}
    abilities_ko = {int(k): v for k, v in json.loads(
        (NAMES_DIR / "korean_ability_names.json").read_text()).items()}

    # Bootstrap from initial map
    cp_to_syl = {int(k, 16): v for k, v in
                 json.loads((NAMES_DIR / "codepoint_map.json").read_text()).items()}

    def all_entries():
        for i in range(GMOVE_NAMES_N):
            cps = read_codepoints(rom, GMOVE_NAMES + i * GMOVE_NAMES_STRIDE,
                                  GMOVE_NAMES_STRIDE)
            yield ("moves", i, cps, moves_ko.get(i, {}).get("ko"))
        for i in range(GABILITY_NAMES_N):
            cps = read_codepoints(rom, GABILITY_NAMES + i * GABILITY_NAMES_STRIDE,
                                  GABILITY_NAMES_STRIDE)
            yield ("abilities", i, cps, abilities_ko.get(i, {}).get("ko"))
        for i in range(GSPECIES_NAMES_N):
            cps = read_codepoints(rom, GSPECIES_NAMES + i * GSPECIES_NAMES_STRIDE,
                                  GSPECIES_NAMES_STRIDE)
            yield ("species", i, cps, species_ko.get(i, {}).get("ko"))

    # Iterative pass: for each entry where len(cps)==len(ko_name), vote each
    # (cp, syllable) pair. Even if they are ambiguous initially, more votes
    # may resolve.
    for iteration in range(5):
        new_resolved = 0
        votes: dict[int, Counter] = defaultdict(Counter)
        for label, idx, cps, ko_name in all_entries():
            if not cps or not ko_name:
                continue
            if len(cps) != len(ko_name):
                continue
            for cp, syl in zip(cps, ko_name):
                votes[cp][syl] += 1
        for cp, ctr in votes.items():
            if cp in cp_to_syl:
                continue
            top_syl, top_count = ctr.most_common(1)[0]
            # Accept if top has >= 2x lead OR is unique
            if len(ctr) == 1 or top_count >= 2 * (ctr.most_common(2)[1][1] if len(ctr) > 1 else 0):
                cp_to_syl[cp] = top_syl
                new_resolved += 1
        # Also: if an entry has only 1 unresolved cp and the rest decode to a
        # prefix/suffix matching ko_name, infer the missing cp.
        for label, idx, cps, ko_name in all_entries():
            if not cps or not ko_name:
                continue
            if len(cps) != len(ko_name):
                continue
            unres = [(i, cp) for i, cp in enumerate(cps) if cp not in cp_to_syl]
            if len(unres) != 1:
                continue
            i, cp = unres[0]
            inferred = ko_name[i]
            cp_to_syl[cp] = inferred
            new_resolved += 1
        print(f"  iteration {iteration}: resolved {new_resolved} new codepoints")
        if new_resolved == 0:
            break

    print(f"Total resolved codepoints: {len(cp_to_syl)}")

    # Save updated map
    (NAMES_DIR / "codepoint_map.json").write_text(
        json.dumps({f"{cp:04X}": syl for cp, syl in sorted(cp_to_syl.items())},
                   ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
