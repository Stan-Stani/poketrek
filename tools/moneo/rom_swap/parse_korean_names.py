#!/usr/bin/env python3
"""Parse PokeAPI CSVs into id -> {ko, en} dictionaries."""
from __future__ import annotations
import csv
import json
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
LANG_KO = 3
LANG_EN = 9


def parse_csv(path, id_col, max_id):
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        out = {}
        for row in reader:
            try:
                rid = int(row[id_col])
                lang = int(row["local_language_id"])
            except (KeyError, ValueError):
                continue
            if rid > max_id:
                continue
            if lang == LANG_KO:
                out.setdefault(rid, {})["ko"] = row["name"]
            elif lang == LANG_EN:
                out.setdefault(rid, {})["en"] = row["name"]
        return out


def main():
    species = parse_csv(OUT_DIR / "pokemon_species_names.csv",
                        "pokemon_species_id", 412)
    moves = parse_csv(OUT_DIR / "move_names.csv", "move_id", 355)
    abilities = parse_csv(OUT_DIR / "ability_names.csv", "ability_id", 80)
    (OUT_DIR / "korean_species_names.json").write_text(
        json.dumps(species, ensure_ascii=False, indent=1))
    (OUT_DIR / "korean_move_names.json").write_text(
        json.dumps(moves, ensure_ascii=False, indent=1))
    (OUT_DIR / "korean_ability_names.json").write_text(
        json.dumps(abilities, ensure_ascii=False, indent=1))
    # Quick sanity
    print(f"species: {len(species)} (sample: 1={species.get(1)} 4={species.get(4)} 25={species.get(25)})")
    print(f"moves: {len(moves)} (sample: 1={moves.get(1)} 33={moves.get(33)})")
    print(f"abilities: {len(abilities)} (sample: 1={abilities.get(1)} 22={abilities.get(22)})")


if __name__ == "__main__":
    main()
