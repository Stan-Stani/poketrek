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
    ("seed-v1",     ASSETS / "seed-vocab-ko.json"),
    ("rom-mine-v2", ASSETS / "seed-vocab-ko-mined.json"),
    ("topik-v2",    ASSETS / "seed-vocab-ko-topik.json"),
    ("rom-species", ASSETS / "seed-vocab-ko-species.json"),
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


def fill_seed_v1(lemma_idx: dict) -> None:
    """The tiny curated seed deck never got lemma-index attribution."""
    path = ASSETS / "seed-vocab-ko.json"
    data = json.loads(path.read_text())
    filled = 0
    for e in data["entries"]:
        info = lemma_idx.get(e.get("korean"))
        if not info: continue
        e.setdefault("firstAreaEncountered", info.get("first_area"))
        e.setdefault("areasReferenced", info.get("areas", []))
        if info.get("source_types"):
            e.setdefault("sourceTypes", info["source_types"])
            e.setdefault("primarySourceType", info.get("primary_source_type", ""))
        e.setdefault("liveRecIds", info.get("rec_ids", []))
        filled += 1
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(f"seed-vocab-ko.json: filled {filled}/{len(data['entries'])} entries from lemma_index")


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
                if e.get(fld) is None or e.get(fld) == "" or e.get(fld) == []:
                    e[fld] = val
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
