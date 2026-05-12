#!/usr/bin/env python3
"""Ensure every sentence card carries the same attribution as its vocab card.

Vocab cards (seed-vocab-ko-*.json) get firstAreaEncountered + areasReferenced
+ sourceTypes + primarySourceType via the lemma_index pipeline. Sentence
cards (sentences-ko-*.json) reference vocabs by `vocabId` but several deck
files didn't get the same fields copied across. This script:

  1. Builds a vocabId -> attribution map from every base seed-vocab-ko-*.json
  2. For every sentence-ko-*.json, fills in missing firstAreaEncountered /
     areasReferenced / sourceTypes / primarySourceType on each entry from
     the matched vocab card.

Also fills in seed-vocab-ko.json itself by looking up each card's korean
in the lemma index.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "app/src/main/assets/moneo"

# vocabId namespaces in this codebase (id prefix -> deck file)
NAMESPACES = [
    # seed-v1 namespace was retired 2026-05-12 (file deleted; entries migrated
    # into seed-vocab-ko-mined.json under rom-mine-v3 ids). Kept here as a note.
    ("rom-mine-v3", ASSETS / "seed-vocab-ko-mined.json"),
    ("topik-v2",    ASSETS / "seed-vocab-ko-topik.json"),
    ("rom-species-2024", ASSETS / "seed-vocab-ko-species.json"),
    ("etymology-roots", ASSETS / "seed-vocab-ko-etymology.json"),
]
SENT_FILES = [
    ASSETS / "sentences-ko-rom.json",
    ASSETS / "sentences-ko-mined.json",
    ASSETS / "sentences-ko-topik.json",
    ASSETS / "sentences-ko-species.json",
    ASSETS / "sentences-ko-etymology.json",
    ASSETS / "sentences-ko-study.json",
    ASSETS / "sentences-ko-themed.json",
    ASSETS / "sentences-ko-themed-mined.json",
    ASSETS / "sentences-ko-themed-topik.json",
    ASSETS / "sentences-ko-themed-species.json",
]
LEMMA = ROOT / "tools/moneo/lemma_area_index.json"

ATTRIB_FIELDS = (
    "firstAreaEncountered", "areasReferenced",
    "sourceTypes", "primarySourceType", "liveRecIds",
)
GENERIC_AREAS = {"rom_mined", "trainer_dialog", "topik_1", "topik_2", "etymology"}


def fill_seed_v1(lemma_idx: dict) -> None:
    """No-op: seed-vocab-ko.json was retired 2026-05-12."""
    pass


def build_vocab_index() -> dict:
    """vocabId -> entry across every base deck."""
    idx = {}
    for ns, path in NAMESPACES:
        data = json.loads(path.read_text())
        for e in data["entries"]:
            korean = e.get("korean")
            if not korean: continue
            vid = f"{ns}:{korean}"
            idx[vid] = e
    return idx


def propagate_to_sentences(vocab_idx: dict) -> None:
    for p in SENT_FILES:
        if not p.exists(): continue
        data = json.loads(p.read_text())
        entries = data.get("entries", [])
        n_attrib = 0
        n_no_match = 0
        for e in entries:
            vid = e.get("vocabId")
            if not vid: continue
            base = vocab_idx.get(vid)
            if not base:
                n_no_match += 1
                continue
            for fld in ATTRIB_FIELDS:
                val = base.get(fld)
                if val is None: continue
                cur = e.get(fld)
                # Always fill if blank
                if cur is None or cur == "" or cur == []:
                    e[fld] = val
                    continue
                # Upgrade firstAreaEncountered / primarySourceType from
                # generic bucket → specific when the base has a specific value
                if fld in ("firstAreaEncountered", "primarySourceType"):
                    if cur in GENERIC_AREAS and val and val not in GENERIC_AREAS:
                        e[fld] = val
                # Union areasReferenced / sourceTypes
                elif fld in ("areasReferenced", "sourceTypes") and isinstance(cur, list) and isinstance(val, list):
                    merged = list(dict.fromkeys((cur or []) + (val or [])))
                    e[fld] = merged
            n_attrib += 1
        p.write_text(json.dumps(data, ensure_ascii=False, indent=1))
        print(f"{p.name}: filled {n_attrib}/{len(entries)} entries from vocab map "
              f"({n_no_match} no-match)")


def main():
    lemma_idx = json.loads(LEMMA.read_text())["lemmas"]
    fill_seed_v1(lemma_idx)
    vocab_idx = build_vocab_index()
    propagate_to_sentences(vocab_idx)


if __name__ == "__main__":
    main()
