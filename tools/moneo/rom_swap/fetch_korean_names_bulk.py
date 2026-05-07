#!/usr/bin/env python3
"""Bulk-fetch Korean Pokemon names via PokeAPI GraphQL endpoint.
"""
from __future__ import annotations
import json
import urllib.request
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
ENDPOINT = "https://beta.pokeapi.co/graphql/v1beta"

QUERIES = {
    "species": """
        query {
            pokemon_v2_pokemonspeciesname(
                where: {language_id: {_eq: 3}, pokemon_species_id: {_lte: 412}},
                order_by: {pokemon_species_id: asc}
            ) {
                pokemon_species_id name
            }
        }
    """,
    "moves": """
        query {
            pokemon_v2_movename(
                where: {language_id: {_eq: 3}, move_id: {_lte: 355}},
                order_by: {move_id: asc}
            ) {
                move_id name
            }
        }
    """,
    "abilities": """
        query {
            pokemon_v2_abilityname(
                where: {language_id: {_eq: 3}, ability_id: {_lte: 80}},
                order_by: {ability_id: asc}
            ) {
                ability_id name
            }
        }
    """,
    "moves_en": """
        query {
            pokemon_v2_movename(
                where: {language_id: {_eq: 9}, move_id: {_lte: 355}},
                order_by: {move_id: asc}
            ) {
                move_id name
            }
        }
    """,
    "abilities_en": """
        query {
            pokemon_v2_abilityname(
                where: {language_id: {_eq: 9}, ability_id: {_lte: 80}},
                order_by: {ability_id: asc}
            ) {
                ability_id name
            }
        }
    """,
    "species_en": """
        query {
            pokemon_v2_pokemonspeciesname(
                where: {language_id: {_eq: 9}, pokemon_species_id: {_lte: 412}},
                order_by: {pokemon_species_id: asc}
            ) {
                pokemon_species_id name
            }
        }
    """,
}


def graphql(query):
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps({"query": query}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main():
    results = {}
    for label, q in QUERIES.items():
        print(f"  fetching {label}...")
        d = graphql(q)
        if "errors" in d:
            print(f"    ERROR: {d['errors']}")
            continue
        results[label] = d["data"]
        # Take first key of data (the only field)
        rows = list(d["data"].values())[0]
        print(f"    got {len(rows)} rows")

    # Pivot into id -> {ko, en}
    species = {}
    for row in results["species"][next(iter(results["species"]))]:
        species[row["pokemon_species_id"]] = {"ko": row["name"]}
    for row in results["species_en"][next(iter(results["species_en"]))]:
        sid = row["pokemon_species_id"]
        species.setdefault(sid, {})["en"] = row["name"]

    moves = {}
    for row in results["moves"][next(iter(results["moves"]))]:
        moves[row["move_id"]] = {"ko": row["name"]}
    for row in results["moves_en"][next(iter(results["moves_en"]))]:
        mid = row["move_id"]
        moves.setdefault(mid, {})["en"] = row["name"]

    abilities = {}
    for row in results["abilities"][next(iter(results["abilities"]))]:
        abilities[row["ability_id"]] = {"ko": row["name"]}
    for row in results["abilities_en"][next(iter(results["abilities_en"]))]:
        aid = row["ability_id"]
        abilities.setdefault(aid, {})["en"] = row["name"]

    (OUT_DIR / "korean_species_names.json").write_text(
        json.dumps(species, ensure_ascii=False, indent=1))
    (OUT_DIR / "korean_move_names.json").write_text(
        json.dumps(moves, ensure_ascii=False, indent=1))
    (OUT_DIR / "korean_ability_names.json").write_text(
        json.dumps(abilities, ensure_ascii=False, indent=1))
    print(f"  species: {len(species)}, moves: {len(moves)}, abilities: {len(abilities)}")


if __name__ == "__main__":
    main()
