#!/usr/bin/env python3
"""Attribute Pokemon move + ability cards to a specific story-area by chaining:

    move/ability → species that learn/have it → species' firstAreaEncountered

Uses PokeAPI CSVs:
  /tmp/pokemon_moves.csv       (pokemon_id, version_group_id, move_id, method, level)
  /tmp/pokemon_abilities.csv   (pokemon_id, ability_id, ...)
  /tmp/moves.csv               (move id → identifier, e.g. "pound")
  /tmp/abilities.csv           (ability id → identifier)

LeafGreen version_group_id = 7.

Pipeline:
  1. Load pokemon_moves.csv filtered to vg=7 + level-up method (1).
     Build move_id → set[pokemon_id].
  2. Load Korean move names from build_name_table_decks output
     (seed-vocab-ko-rom-names.json moves) which includes the move's
     english gloss; match by english identifier → move_id.
  3. For each move card, find pokemon_id of the lowest-dex species
     that learns the move; look up that species' firstAreaEncountered
     in seed-vocab-ko-species.json.
  4. Same chain for abilities (pokemon_abilities.csv).
"""
from __future__ import annotations
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "app/src/main/assets/moneo"
LG_VG = 7  # firered-leafgreen


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def main():
    # ---- 1. Move id → species ids that learn it via level-up in LG ----
    move_to_species: dict[int, set[int]] = {}
    species_min_level: dict[tuple[int, int], int] = {}
    with open("/tmp/pokemon_moves.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if int(row["version_group_id"]) != LG_VG: continue
            if int(row["pokemon_move_method_id"]) != 1: continue  # level-up
            pid = int(row["pokemon_id"])
            mid = int(row["move_id"])
            move_to_species.setdefault(mid, set()).add(pid)
            level = int(row["level"] or 0)
            key = (mid, pid)
            if key not in species_min_level or level < species_min_level[key]:
                species_min_level[key] = level
    print(f"move learnsets: {len(move_to_species)} moves; "
          f"{sum(len(s) for s in move_to_species.values())} (move, species) pairs")

    # ---- 2. Move identifier ("pound") → move_id ----
    move_id_by_ident = {}
    with open("/tmp/moves.csv") as f:
        for row in csv.DictReader(f):
            move_id_by_ident[row["identifier"]] = int(row["id"])

    # ---- 3. Ability id → species ids ----
    ability_to_species: dict[int, set[int]] = {}
    with open("/tmp/pokemon_abilities.csv") as f:
        for row in csv.DictReader(f):
            aid = int(row["ability_id"])
            pid = int(row["pokemon_id"])
            ability_to_species.setdefault(aid, set()).add(pid)
    ability_id_by_ident = {}
    with open("/tmp/abilities.csv") as f:
        for row in csv.DictReader(f):
            ability_id_by_ident[row["identifier"]] = int(row["id"])

    # ---- 4. Load species deck to get species pokeapi_id → firstAreaEncountered ----
    species = json.loads((ASSETS / "seed-vocab-ko-species.json").read_text())
    # species cards have `source: "gSpeciesNames[N]"` where N = ROM index = dex number
    species_area_by_dex: dict[int, str] = {}
    species_korean_by_dex: dict[int, str] = {}
    for e in species["entries"]:
        src = e.get("source", "")
        m = re.match(r"gSpeciesNames\[(\d+)\]", src)
        if not m: continue
        dex = int(m.group(1))
        fa = e.get("firstAreaEncountered")
        if fa:
            species_area_by_dex[dex] = fa
            species_korean_by_dex[dex] = e["korean"]
    print(f"species deck: {len(species_area_by_dex)} dex entries with attribution")

    # ---- 5. Load area ordinals for picking lowest-ordinal area ----
    areas = json.loads((ASSETS / "areas.json").read_text())["areas"]
    area_ord = {a["id"]: a["ordinal"] for a in areas}
    area_ord["rom_mined"] = 99
    GENERIC = {"rom_mined", "trainer_dialog", "topik_1", "topik_2", "etymology"}

    def best_area_from_species(species_ids: set, learn_levels: dict | None = None) -> tuple[str | None, list[str]]:
        """Among the given species, pick the lowest-ordinal first-encounter area."""
        candidate_areas = []
        for sid in species_ids:
            fa = species_area_by_dex.get(sid)
            if not fa or fa in GENERIC: continue
            candidate_areas.append(fa)
        if not candidate_areas: return None, []
        candidate_areas.sort(key=lambda a: area_ord.get(a, 999999))
        return candidate_areas[0], list(dict.fromkeys(candidate_areas))

    # ---- 6. Attribute moves ----
    mined = json.loads((ASSETS / "seed-vocab-ko-mined.json").read_text())
    move_promoted = 0
    ability_promoted = 0

    # Build move-id by english gloss for cards that have gloss
    for e in mined["entries"]:
        if e.get("firstAreaEncountered") and e["firstAreaEncountered"] not in GENERIC:
            continue  # already specific
        gloss = e.get("gloss", "")
        # Move gloss format: "Karate Chop (move)"
        m_move = re.match(r"^(.+?) \(move\)$", gloss)
        m_ability = re.match(r"^(.+?) \(ability\)$", gloss)
        if m_move:
            ename = slugify(m_move.group(1))
            mid = move_id_by_ident.get(ename)
            if not mid: continue
            species_ids = move_to_species.get(mid, set())
            if not species_ids: continue
            best, all_areas = best_area_from_species(species_ids)
            if not best: continue
            e["firstAreaEncountered"] = best
            existing_areas = set(e.get("areasReferenced") or [])
            existing_areas.update(all_areas)
            e["areasReferenced"] = sorted(existing_areas)
            # Tag source — move via learnset
            move_promoted += 1
        elif m_ability:
            ename = slugify(m_ability.group(1))
            aid = ability_id_by_ident.get(ename)
            if not aid: continue
            species_ids = ability_to_species.get(aid, set())
            if not species_ids: continue
            best, all_areas = best_area_from_species(species_ids)
            if not best: continue
            e["firstAreaEncountered"] = best
            existing_areas = set(e.get("areasReferenced") or [])
            existing_areas.update(all_areas)
            e["areasReferenced"] = sorted(existing_areas)
            ability_promoted += 1

    print(f"\npromoted via learnset chain:")
    print(f"  moves: {move_promoted}")
    print(f"  abilities: {ability_promoted}")

    # Save
    notes = mined.get("notes", [])
    if not isinstance(notes, list): notes = [notes]
    notes.append(
        f"attribute_moves_via_learnsets: "
        f"+{move_promoted} moves, +{ability_promoted} abilities promoted "
        f"to specific story-area via PokeAPI learnset (LG vg=7) chain."
    )
    mined["notes"] = notes
    (ASSETS / "seed-vocab-ko-mined.json").write_text(
        json.dumps(mined, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
