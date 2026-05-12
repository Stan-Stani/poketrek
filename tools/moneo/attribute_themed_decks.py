#!/usr/bin/env python3
"""Propagate attribution (firstAreaEncountered, areasReferenced, sourceTypes,
primarySourceType) from the base decks to the themed-* derivatives.

Themed decks are LLM-written example sentences keyed by vocabId. They don't
contain ROM-extracted text; we just need to match each sentence's vocabId
to the corresponding base vocab card and copy the attribution fields.

Inputs:
  app/src/main/assets/moneo/seed-vocab-ko-mined.json   (rom-mine-v3:lemma)
  app/src/main/assets/moneo/seed-vocab-ko-topik.json   (topik-v2:lemma)
  app/src/main/assets/moneo/seed-vocab-ko-species.json (rom-species-2024:name)
  + matching sentences-ko-themed-{mined,topik,species,themed}.json files

Outputs: rewrites the themed files in place with attribution merged in.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "app/src/main/assets/moneo"

# Map base deck path -> id_namespace (used to look up vocabId -> entry)
BASES = [
    (ASSETS / "seed-vocab-ko-mined.json",   "rom-mine-v3"),
    (ASSETS / "seed-vocab-ko-topik.json",   "topik-v2"),
    (ASSETS / "seed-vocab-ko-species.json", "rom-species-2024"),
    (ASSETS / "seed-vocab-ko.json",         "seed-v1"),
]

THEMED = [
    ASSETS / "sentences-ko-themed.json",
    ASSETS / "sentences-ko-themed-mined.json",
    ASSETS / "sentences-ko-themed-topik.json",
    ASSETS / "sentences-ko-themed-species.json",
]


def build_index():
    """Build vocabId -> base-entry index from all base decks."""
    by_id = {}
    for path, ns in BASES:
        data = json.loads(path.read_text())
        for e in data["entries"]:
            korean = e.get("korean")
            if not korean: continue
            vid = f"{ns}:{korean}"
            by_id[vid] = e
    return by_id


def main():
    base_idx = build_index()
    for tpath in THEMED:
        data = json.loads(tpath.read_text())
        entries = data["entries"]
        attributed = 0
        unmatched = 0
        for e in entries:
            vid = e.get("vocabId")
            if not vid: continue
            base = base_idx.get(vid)
            if not base:
                unmatched += 1
                continue
            # Carry over attribution fields
            if base.get("firstAreaEncountered"):
                e["firstAreaEncountered"] = base["firstAreaEncountered"]
            if base.get("areasReferenced"):
                e["areasReferenced"] = base["areasReferenced"]
            if base.get("sourceTypes"):
                e["sourceTypes"] = base["sourceTypes"]
            if base.get("primarySourceType"):
                e["primarySourceType"] = base["primarySourceType"]
            attributed += 1
        # Append a regen note
        notes = data.get("notes", [])
        if not isinstance(notes, list):
            notes = [notes] if notes else []
        notes.append(
            f"Attribution propagated from base decks; "
            f"{attributed} matched, {unmatched} unmatched of {len(entries)}."
        )
        data["notes"] = notes
        tpath.write_text(json.dumps(data, ensure_ascii=False, indent=1))
        print(f"  {tpath.name}: {attributed}/{len(entries)} attributed, "
              f"{unmatched} unmatched")


if __name__ == "__main__":
    main()
