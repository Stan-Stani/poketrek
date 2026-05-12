#!/usr/bin/env python3
"""Rebuild the shipped mined vocab + sentences decks from scratch.

Combines:
  - tools/moneo/seed-vocab-ko-live-mined.json  (fresh dialog mining via mine_vocab)
  - tools/moneo/seed-vocab-ko-rom-names.json   (move + ability extraction via
                                                build_name_table_decks)

Attributes each entry via tools/moneo/lemma_area_index.json (now including
sourceTypes/primarySourceType from the multi-pass tagging).

Writes:
  - app/src/main/assets/moneo/seed-vocab-ko-mined.json
  - app/src/main/assets/moneo/sentences-ko-mined.json

Replaces the prior merged deck (which carried 2010-vintage kana-mojibake-
contaminated entries).
"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ASSETS = ROOT / "app/src/main/assets/moneo"

VOCAB_LIVE   = HERE / "seed-vocab-ko-live-mined.json"
VOCAB_NAMES  = HERE / "seed-vocab-ko-rom-names.json"
SENTS_LIVE   = HERE / "sentences-ko-live-mined.json"
SENTS_NAMES  = HERE / "sentences-ko-rom-names.json"
LEMMA_INDEX  = HERE / "lemma_area_index.json"

OUT_VOCAB = ASSETS / "seed-vocab-ko-mined.json"
OUT_SENTS = ASSETS / "sentences-ko-mined.json"


def load(p): return json.loads(p.read_text())


def main():
    lemmas = load(LEMMA_INDEX).get("lemmas", {})

    vocab_live  = load(VOCAB_LIVE)["entries"]
    vocab_names = load(VOCAB_NAMES)["entries"]
    sents_live  = load(SENTS_LIVE)["entries"]
    sents_names = load(SENTS_NAMES)["entries"]

    # Vocab: dedupe by Korean; prefer name-table entries (they have richer
    # source-type tagging like "pokemon_move"), then dialog entries.
    by_korean: dict[str, dict] = {}
    for e in vocab_names:
        by_korean[e["korean"]] = dict(e)
    for e in vocab_live:
        if e["korean"] in by_korean:
            continue
        by_korean[e["korean"]] = dict(e)

    # Attribute via lemma index (only entries whose lemma is in the index get
    # area data; name-table entries already carry their own attribution from
    # build_name_table_decks).
    attributed = 0
    for ko, entry in by_korean.items():
        info = lemmas.get(ko)
        if info:
            # Don't override the canonical name-table attribution if present;
            # do union the area sets so name-table cards also surface in
            # dialog areas where they're mentioned.
            existing_first = entry.get("firstAreaEncountered")
            entry.setdefault("liveRecIds", info.get("rec_ids", []))
            entry.setdefault("areasReferenced", info.get("areas", []))
            if not existing_first or existing_first == "rom_mined":
                entry["firstAreaEncountered"] = info.get("first_area", "rom_mined")
            # Merge area lists
            merged_areas = list(dict.fromkeys((entry.get("areasReferenced") or []) + info.get("areas", [])))
            entry["areasReferenced"] = merged_areas
            # Union source types
            existing_st = set(entry.get("sourceTypes", []))
            existing_st.update(info.get("source_types", []))
            entry["sourceTypes"] = sorted(existing_st)
            if not entry.get("primarySourceType"):
                entry["primarySourceType"] = info.get("primary_source_type", "")
            attributed += 1
        else:
            entry.setdefault("sourceTypes", entry.get("sourceTypes", []) or [])
            entry.setdefault("primarySourceType", entry.get("primarySourceType", ""))

    vocab_out = {
        "version": 1,
        "sourceTag": "rom-mine-v3",
        "notes": [
            "Regenerated from 2024 Korean patch decode. Combines mine_vocab "
            "output (dialog lemmas via mecab-ko) with build_name_table_decks "
            "output (gMoveNames + gAbilityNames). Per-entry sourceTypes carry "
            "the pipeline pass(es) that produced the lemma.",
            f"Total entries: {len(by_korean)}. Lemma-index-attributed: {attributed}.",
        ],
        "entries": list(by_korean.values()),
    }
    OUT_VOCAB.write_text(json.dumps(vocab_out, ensure_ascii=False, indent=1))
    print(f"vocab: {len(by_korean)} entries -> {OUT_VOCAB.relative_to(ROOT)}")
    print(f"  attributed via lemma_index: {attributed}")

    # Sentences: dedupe by (vocabId, korean); same source preference.
    # Remap any stale rom-mine-v2 prefix from older intermediate files to the
    # current rom-mine-v3 namespace before deduping — the shipped seed bumped
    # to v3 and the SeedLoader only resolves matching prefixes.
    def _v3(s):
        vid = s.get("vocabId", "")
        if vid.startswith("rom-mine-v2:"):
            s["vocabId"] = "rom-mine-v3:" + vid.split(":", 1)[1]
        return s
    seen: set = set()
    sent_entries: list = []
    for s in sents_names:
        s = _v3(dict(s))
        key = (s.get("vocabId"), s.get("korean"))
        if key in seen: continue
        seen.add(key)
        sent_entries.append(s)
    for s in sents_live:
        s2 = _v3(dict(s))
        key = (s2.get("vocabId"), s2.get("korean"))
        if key in seen: continue
        seen.add(key)
        # Attribute via lemma index using target lemma extracted from vocabId
        vid = s2.get("vocabId", "")
        lemma = vid.split(":", 1)[1] if ":" in vid else s2.get("targetForm")
        if lemma and lemma in lemmas:
            info = lemmas[lemma]
            s2.setdefault("areasReferenced", info.get("areas", []))
            s2["firstAreaEncountered"] = info.get("first_area", s2.get("areaId", "rom_mined"))
            s2["sourceTypes"] = info.get("source_types", [])
            s2["primarySourceType"] = info.get("primary_source_type", "")
        sent_entries.append(s2)

    sent_out = {
        "version": 1,
        "sourceTag": "rom-mine-v3",
        "notes": [
            "Regenerated from 2024 Korean patch decode. Sentences come from "
            "mine_vocab (one example per dialog lemma) + name-table decks "
            "(one templated sentence per move/ability)."
        ],
        "entries": sent_entries,
    }
    OUT_SENTS.write_text(json.dumps(sent_out, ensure_ascii=False, indent=1))
    print(f"sentences: {len(sent_entries)} entries -> {OUT_SENTS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
