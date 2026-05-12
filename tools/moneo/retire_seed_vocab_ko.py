#!/usr/bin/env python3
"""Retire app/src/main/assets/moneo/seed-vocab-ko.json.

Steps:
  1. For each of the 45 seed entries:
     a. If already attributed (firstAreaEncountered set) — carry attribution.
     b. Else search corpus for the stem; if hits exist, compute first area
        from the rec_ids' map_area_index attribution. Hand-attribute.
     c. If no corpus presence — drop the entry (cardinal directions, etc).
  2. Migrate surviving entries into seed-vocab-ko-mined.json (rom-mine-v2:
     namespace) so the runtime keeps them.
  3. Rewrite sentences-ko-rom.json and sentences-ko-study.json vocabId
     fields from `seed-v1:X` to `rom-mine-v2:X` so they stay valid.
  4. Delete seed-vocab-ko.json from assets.
  5. Patch MoneoModule.kt to drop the SeedLoader.loadFromAssets() call.
"""
from __future__ import annotations
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "app/src/main/assets/moneo"
TOOLS = ROOT / "tools/moneo"

SEED_VOCAB = ASSETS / "seed-vocab-ko.json"
MINED_VOCAB = ASSETS / "seed-vocab-ko-mined.json"
CORPUS = ASSETS / "corpus.ko.json"
MAP_AREA = TOOLS / "map_area_index.json"
AREAS = ASSETS / "areas.json"
SENT_ROM = ASSETS / "sentences-ko-rom.json"
SENT_STUDY = ASSETS / "sentences-ko-study.json"
SENT_THEMED = ASSETS / "sentences-ko-themed.json"
MONEO_MODULE = ROOT / "app/src/main/java/com/poketrek/moneo/MoneoModule.kt"


def hand_attribute_word(word: str, corpus: list, rec_to_areas: dict,
                        area_ordinals: dict) -> tuple[str | None, list[str], list[int]]:
    """For a seed word, find its first-encounter area by searching the corpus.

    Returns (first_area, all_areas_sorted, sample_rec_ids).
    """
    stem = word[:-1] if word.endswith("다") and len(word) >= 2 else word
    if not stem: return None, [], []
    hit_rec_ids = []
    area_counter: Counter = Counter()
    for r in corpus:
        text = r.get("text", "")
        if stem not in text: continue
        rid = r["id"]
        hit_rec_ids.append(rid)
        for aid in rec_to_areas.get(rid, set()):
            area_counter[aid] += 1
        if len(hit_rec_ids) >= 200: break
    if not hit_rec_ids: return None, [], []
    # Pick first_area by lowest ordinal among hit areas
    ordered = sorted(area_counter.keys(),
                     key=lambda a: area_ordinals.get(a, 999999) if area_ordinals.get(a, -1) >= 0 else 999999)
    first_area = ordered[0] if ordered else "rom_mined"
    return first_area, ordered, hit_rec_ids[:5]


def main():
    seed = json.loads(SEED_VOCAB.read_text())
    mined = json.loads(MINED_VOCAB.read_text())
    corpus = json.loads(CORPUS.read_text())["records"]
    map_area = json.loads(MAP_AREA.read_text())
    areas = json.loads(AREAS.read_text())["areas"]
    area_ord = {a["id"]: a["ordinal"] for a in areas}
    area_ord["rom_mined"] = 99
    area_ord["trainer_dialog"] = 51

    # rec_id -> set[area_id] from resolved map_area_index
    rec_to_areas: dict[int, set] = {}
    for aid, info in map_area.get("resolved_areas", {}).items():
        for rid in info.get("recIds", []):
            rec_to_areas.setdefault(rid, set()).add(aid)

    # Build index of mined deck (rom-mine-v2: namespace)
    mined_by_korean = {e["korean"]: e for e in mined["entries"]}

    migrated_pre = 0       # already attributed in seed
    hand_attributed = 0    # found in corpus, attribution computed now
    dropped = []           # no corpus presence
    already_in_mined = 0   # mined deck already has this korean (no-op)

    for e in seed["entries"]:
        word = e["korean"]
        if word in mined_by_korean:
            already_in_mined += 1
            continue
        # Use existing attribution if seed-vocab-ko provided one
        if e.get("firstAreaEncountered"):
            new_entry = dict(e)
            new_entry["sourceTag"] = "seed-v1-retired"  # provenance trail
            mined["entries"].append(new_entry)
            mined_by_korean[word] = new_entry
            migrated_pre += 1
            continue
        # Hand-attribute via corpus search
        first_area, all_areas, rec_ids = hand_attribute_word(
            word, corpus, rec_to_areas, area_ord)
        if first_area is None:
            dropped.append(word)
            continue
        new_entry = dict(e)
        new_entry["firstAreaEncountered"] = first_area
        new_entry["areasReferenced"] = all_areas
        new_entry["liveRecIds"] = rec_ids
        new_entry["sourceTag"] = "seed-v1-retired-handattr"
        # We don't have source_types for these (mecab filtered them out);
        # tag as npc_dialog if corpus presence is in story areas, else system_text
        if any(a in all_areas for a in area_ord if area_ord.get(a, 999) < 99):
            new_entry["sourceTypes"] = ["npc_dialog"]
            new_entry["primarySourceType"] = "npc_dialog"
        else:
            new_entry["sourceTypes"] = ["system_text"]
            new_entry["primarySourceType"] = "system_text"
        mined["entries"].append(new_entry)
        mined_by_korean[word] = new_entry
        hand_attributed += 1

    print(f"  pre-attributed: {migrated_pre}")
    print(f"  hand-attributed via corpus: {hand_attributed}")
    print(f"  already in mined deck: {already_in_mined}")
    print(f"  dropped (no corpus presence): {len(dropped)} → {dropped}")

    # Update mined deck notes
    notes = mined.get("notes", [])
    if not isinstance(notes, list): notes = [notes]
    notes.append(
        f"Retired seed-vocab-ko.json. Migrated {migrated_pre + hand_attributed} "
        f"entries ({hand_attributed} hand-attributed via corpus search). "
        f"Dropped {len(dropped)}: {dropped}."
    )
    mined["notes"] = notes
    MINED_VOCAB.write_text(json.dumps(mined, ensure_ascii=False, indent=1))
    print(f"  mined deck: -> {len(mined['entries'])} entries")

    # Renamespace sentence files: seed-v1:X -> rom-mine-v2:X
    for sent_path in (SENT_ROM, SENT_STUDY, SENT_THEMED):
        if not sent_path.exists(): continue
        d = json.loads(sent_path.read_text())
        rewritten = 0
        kept = []
        for s in d["entries"]:
            vid = s.get("vocabId", "")
            if vid.startswith("seed-v1:"):
                korean = vid.split(":", 1)[1]
                if korean in [x for x in dropped]:
                    continue  # drop orphan sentences for genuinely-absent words
                s["vocabId"] = f"rom-mine-v2:{korean}"
                rewritten += 1
            kept.append(s)
        d["entries"] = kept
        sent_path.write_text(json.dumps(d, ensure_ascii=False, indent=1))
        print(f"  {sent_path.name}: rewrote {rewritten} seed-v1 vocabIds; "
              f"{len(kept)} sentences kept")

    # Delete seed-vocab-ko.json
    SEED_VOCAB.unlink()
    print(f"  deleted {SEED_VOCAB.relative_to(ROOT)}")

    # Patch MoneoModule.kt
    src = MONEO_MODULE.read_text()
    old_block = (
        '        val vocabSeed = runCatching { SeedLoader.loadFromAssets(context) }.getOrElse { emptyList() }\n'
    )
    new_block = (
        '        // seed-vocab-ko.json retired 2026-05-12 — its 45 entries were\n'
        '        // hand-curated MVP placeholders, now migrated into seed-vocab-\n'
        '        // ko-mined.json with rom-mine-v2 ids. SeedLoader is still used\n'
        '        // for the larger mined/topik/species/etymology decks below.\n'
        '        val vocabSeed = emptyList<VocabEntry>()\n'
    )
    if old_block in src:
        src = src.replace(old_block, new_block)
        MONEO_MODULE.write_text(src)
        print(f"  patched {MONEO_MODULE.relative_to(ROOT)}: removed seed-vocab-ko load")


if __name__ == "__main__":
    main()
