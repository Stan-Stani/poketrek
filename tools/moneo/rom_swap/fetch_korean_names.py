#!/usr/bin/env python3
"""Fetch canonical Korean Pokemon species, move, and ability names from PokeAPI.

Outputs JSON files we can use to triangulate the 16-bit glyph codepoint
encoding used in the 2024 patched ROM's gMoveNames/gAbilityNames/gSpeciesNames.
"""
from __future__ import annotations
import json
import sys
import time
import urllib.request
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
SPECIES_OUT = OUT_DIR / "korean_species_names.json"
MOVES_OUT = OUT_DIR / "korean_move_names.json"
ABILITIES_OUT = OUT_DIR / "korean_ability_names.json"


def fetch_json(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                return json.loads(r.read())
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(1)


def get_korean_name(payload, fallback="?"):
    for n in payload.get("names", []):
        lang = n.get("language", {}).get("name")
        if lang == "ko":
            return n["name"]
    return fallback


def fetch_species(n=412):
    out = {}
    for i in range(1, n + 1):
        try:
            d = fetch_json(f"https://pokeapi.co/api/v2/pokemon-species/{i}/")
            out[i] = get_korean_name(d)
            if i % 25 == 0:
                print(f"  species {i}/{n} = {out[i]}")
        except Exception as e:
            print(f"  species {i}: ERROR {e}", file=sys.stderr)
            out[i] = None
    return out


def fetch_moves(n=355):
    out = {}
    for i in range(1, n + 1):
        try:
            d = fetch_json(f"https://pokeapi.co/api/v2/move/{i}/")
            out[i] = {
                "ko": get_korean_name(d),
                "en": d.get("name", ""),
            }
            if i % 25 == 0:
                print(f"  move {i}/{n} = {out[i]['ko']} ({out[i]['en']})")
        except Exception as e:
            print(f"  move {i}: ERROR {e}", file=sys.stderr)
            out[i] = None
    return out


def fetch_abilities(n=78):
    out = {}
    for i in range(1, n + 1):
        try:
            d = fetch_json(f"https://pokeapi.co/api/v2/ability/{i}/")
            out[i] = {
                "ko": get_korean_name(d),
                "en": d.get("name", ""),
            }
            if i % 10 == 0:
                print(f"  ability {i}/{n} = {out[i]['ko']} ({out[i]['en']})")
        except Exception as e:
            print(f"  ability {i}: ERROR {e}", file=sys.stderr)
            out[i] = None
    return out


def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else ["species", "moves", "abilities"]
    if "species" in targets:
        print("Fetching species...")
        sp = fetch_species()
        SPECIES_OUT.write_text(json.dumps(sp, ensure_ascii=False, indent=1))
        print(f"  saved -> {SPECIES_OUT}")
    if "moves" in targets:
        print("Fetching moves...")
        mv = fetch_moves()
        MOVES_OUT.write_text(json.dumps(mv, ensure_ascii=False, indent=1))
        print(f"  saved -> {MOVES_OUT}")
    if "abilities" in targets:
        print("Fetching abilities...")
        ab = fetch_abilities()
        ABILITIES_OUT.write_text(json.dumps(ab, ensure_ascii=False, indent=1))
        print(f"  saved -> {ABILITIES_OUT}")


if __name__ == "__main__":
    main()
