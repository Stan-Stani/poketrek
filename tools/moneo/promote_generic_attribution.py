#!/usr/bin/env python3
"""Promote every card stuck in a generic bucket (rom_mined / topik_1 /
topik_2 / trainer_dialog / etymology) to a specific story-progression area
when one can be derived from corpus presence.

Strategy per card (in priority order):

  1. If the card's vocab.korean (or its verb stem, X minus the trailing 다)
     appears in any corpus record whose offset is reached by
     map_area_index → use the lowest-ordinal area among those records.

  2. If it appears only in static records, fall through to:
     a. species_obtain_index — if any matching rec_id is a Pokedex entry
        for a species in the obtain-index, use that species' first-encounter
        area.
     b. item_obtain_index — same for item descriptions.

  3. If nothing maps, leave it at the generic bucket. (Real "system only"
     vocab like 사인 / 게임 / 카트리지 has no in-world story-area.)

Outputs: rewrites every seed-vocab-ko-{mined,topik,species,etymology}.json
in place, then re-runs propagate_vocab_to_sentences.py so the matching
sentence files inherit the upgraded attribution.
"""
from __future__ import annotations
import json
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "app/src/main/assets/moneo"
TOOLS = ROOT / "tools/moneo"

GENERIC = {"rom_mined", "trainer_dialog", "topik_1", "topik_2", "etymology"}
DECKS = [
    "seed-vocab-ko-mined.json",
    "seed-vocab-ko-topik.json",
    "seed-vocab-ko-species.json",
    "seed-vocab-ko-etymology.json",
]


def main():
    corpus = json.loads((ASSETS / "corpus.ko.json").read_text())["records"]
    map_area = json.loads((TOOLS / "map_area_index.json").read_text())
    areas = json.loads((ASSETS / "areas.json").read_text())["areas"]
    area_ord = {a["id"]: a["ordinal"] for a in areas}

    # Reverse: rec_id -> set[area_id] from walk-resolved areas
    rec_to_areas: dict[int, set] = {}
    for aid, info in map_area.get("resolved_areas", {}).items():
        for rid in info.get("recIds", []):
            rec_to_areas.setdefault(rid, set()).add(aid)

    # Fold in item/pokedex obtain indexes (they pin static-only records to
    # buy/encounter areas)
    for idx_path, key in [
        ("item_obtain_index.json",   "area_to_item_rec_ids"),
        ("pokedex_obtain_index.json", "area_to_pokedex_rec_ids"),
    ]:
        p = TOOLS / idx_path
        if not p.exists(): continue
        data = json.loads(p.read_text())
        for aid, rids in (data.get(key) or {}).items():
            for rid in rids:
                rec_to_areas.setdefault(rid, set()).add(aid)

    def rank(a: str) -> int:
        o = area_ord.get(a, 999999)
        return o if o >= 0 else 999999

    def best_area_for_word(word: str) -> tuple[str | None, list[str], list[int]]:
        """Return (best_area, sorted_areas, sample_rec_ids) by scanning corpus
        for word/stem and intersecting with rec_to_areas."""
        stem = word[:-1] if word.endswith("다") and len(word) >= 2 else word
        if not stem: return None, [], []
        hit_areas: Counter = Counter()
        sample_recs: list[int] = []
        for r in corpus:
            text = r.get("text", "")
            if stem not in text: continue
            rid = r["id"]
            for aid in rec_to_areas.get(rid, set()):
                if aid in GENERIC: continue
                hit_areas[aid] += 1
            if len(sample_recs) < 5:
                sample_recs.append(rid)
        if not hit_areas: return None, [], sample_recs
        ordered = sorted(hit_areas, key=rank)
        return ordered[0], ordered, sample_recs

    total_promoted = 0
    for deck_name in DECKS:
        p = ASSETS / deck_name
        if not p.exists(): continue
        deck = json.loads(p.read_text())
        entries = deck["entries"]
        promoted = 0
        unchanged = 0
        for e in entries:
            fa = e.get("firstAreaEncountered")
            if fa and fa not in GENERIC: continue  # already specific
            word = e.get("korean")
            if not word: continue
            best, all_areas, recs = best_area_for_word(word)
            if not best:
                unchanged += 1
                continue
            e["firstAreaEncountered"] = best
            # Union new areas onto existing areasReferenced
            existing = e.get("areasReferenced") or []
            merged = list(dict.fromkeys(all_areas + existing))
            e["areasReferenced"] = merged
            if not e.get("liveRecIds"):
                e["liveRecIds"] = recs
            promoted += 1

        notes = deck.get("notes", [])
        if not isinstance(notes, list):
            notes = [notes] if notes else []
        notes.append(
            f"promote_generic_attribution: {promoted} cards moved from "
            f"generic bucket → specific story area via corpus-stem search."
        )
        deck["notes"] = notes
        p.write_text(json.dumps(deck, ensure_ascii=False, indent=1))
        print(f"  {deck_name}: promoted {promoted}, unchanged {unchanged}")
        total_promoted += promoted

    print(f"\ntotal promoted: {total_promoted}")
    # Cascade to sentence files
    print("\nre-running propagate_vocab_to_sentences.py ...")
    subprocess.run(["python3", str(TOOLS / "propagate_vocab_to_sentences.py")],
                   check=True)


if __name__ == "__main__":
    main()
