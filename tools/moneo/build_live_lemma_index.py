import json
import struct
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rom_config import ROM_PATH, TRAINER_DIALOG_REGIONS_2024  # noqa: E402

from mine_vocab import (
    mecab_lemmatize,
    is_hangul,
    is_kana_shape_token,
    has_no_batchim,
    is_phonetic_noise,
    _MECAB,
)

CORPUS_PATH = Path(__file__).resolve().parent / "corpus.ko.live.json"
STATIC_CORPUS_PATH = Path(__file__).resolve().parents[2] / "app/src/main/assets/moneo/corpus.ko.json"
MAP_AREA_PATH = Path(__file__).resolve().parent / "map_area_index.json"
AREAS_PATH = Path(__file__).resolve().parents[2] / "app/src/main/assets/moneo/areas.json"
OUTPUT_PATH = Path(__file__).resolve().parent / "lemma_area_index.json"

# Sentinel area for vocabulary that exists only in the static corpus
# (Pokédex entries, item descriptions, menu strings). These records are
# not tied to a specific story-progression area, but they ARE in the
# game -- you can read them once you have the Pokédex (Pallet onwards)
# or buy the corresponding item. Tagging with the existing rom_mined
# area_id surfaces them as attributed without preempting canonical
# area assignments (rom_mined ordinal 99 > all canonical area ordinals).
STATIC_ONLY_AREA_ID = "rom_mined"


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    if _MECAB is None:
        print("MeCab-ko not available. Please install mecab-python3.", file=sys.stderr)
        sys.exit(1)

    corpus_data = load_json(CORPUS_PATH)
    records = corpus_data["records"]
    id_to_record = {r["id"]: r for r in records}

    # Also index the static corpus by id so map-walker-reached rec_ids
    # (which now come from the 2024 comprehensive static corpus) can be
    # looked up in the per-area pass below. Prior to the 2024 swap, all
    # walker hits were live-only; now they're static.
    static_corpus_for_lookup = load_json(STATIC_CORPUS_PATH)
    for r in static_corpus_for_lookup["records"]:
        id_to_record.setdefault(r["id"], r)

    map_data = load_json(MAP_AREA_PATH)
    resolved_areas = map_data["resolved_areas"]

    # area_id -> ordinal (from map_area_index)
    area_ordinals = {aid: info["ordinal"] for aid, info in resolved_areas.items()}

    # rec_id -> set[area_id]
    rec2areas = defaultdict(set)
    reachable_rec_ids = set()
    for aid, info in resolved_areas.items():
        for rid in info["recIds"]:
            rec2areas[rid].add(aid)
            reachable_rec_ids.add(rid)

    # Accumulate lemma data
    lemma_areas = defaultdict(set)       # lemma -> set of area_id
    lemma_rec_ids = defaultdict(list)    # lemma -> list of rec_id (max 5)

    records_tokenized = 0
    for rid in sorted(reachable_rec_ids):
        rec = id_to_record.get(rid)
        if not rec:
            continue
        text = rec.get("text", "")
        if not text:
            continue
        records_tokenized += 1
        try:
            tokens = mecab_lemmatize(text)
        except Exception:
            # skip sentences that fail to parse
            continue

        areas_for_rec = rec2areas.get(rid, set())
        for lemma, pos, surface in tokens:
            # Filtering
            if not (2 <= len(lemma) <= 5):
                continue
            if not all(is_hangul(c) for c in lemma):
                continue
            if is_phonetic_noise(lemma):
                continue
            if is_kana_shape_token(lemma):
                continue
            if pos == "noun" and len(lemma) >= 3 and has_no_batchim(lemma):
                continue

            lemma_areas[lemma].update(areas_for_rec)
            if len(lemma_rec_ids[lemma]) < 5 and rid not in lemma_rec_ids[lemma]:
                lemma_rec_ids[lemma].append(rid)

    # Second pass: static corpus (Pokédex / item descriptions / menu strings).
    # Records here aren't tied to a specific story-progression area, so we
    # tag every static-extracted lemma with STATIC_ONLY_AREA_ID (rom_mined,
    # ordinal 99). Lemmas that ALSO appear in live-region records keep their
    # canonical area as first_area because canonical ordinals (1..50) beat
    # rom_mined's 99. Lemmas appearing ONLY in static text get rom_mined as
    # their first_area -- which is at least an honest "yes, this is in the
    # game's text somewhere" attribution.
    static_corpus = load_json(STATIC_CORPUS_PATH)
    static_records_tokenized = 0
    for rec in static_corpus["records"]:
        text = rec.get("text", "")
        if not text or rec.get("unknown", 0) > 1:
            continue
        static_records_tokenized += 1
        try:
            tokens = mecab_lemmatize(text)
        except Exception:
            continue
        for lemma, pos, surface in tokens:
            if not (2 <= len(lemma) <= 5):
                continue
            if not all(is_hangul(c) for c in lemma):
                continue
            if is_phonetic_noise(lemma):
                continue
            if is_kana_shape_token(lemma):
                continue
            if pos == "noun" and len(lemma) >= 3 and has_no_batchim(lemma):
                continue
            lemma_areas[lemma].add(STATIC_ONLY_AREA_ID)
            # Don't override live-region rec_ids; only attach static rec_id
            # if there are no live records for this lemma yet.
            if not lemma_rec_ids[lemma] and len(lemma_rec_ids[lemma]) < 5:
                lemma_rec_ids[lemma].append(rec["id"])

    # Third pass: trainer-dialog ROM table region.
    # Scans the GBA ROM for pointers into trainer/sign-dialog text,
    # tokenises those records and tags their lemmas with a dedicated area.
    TRAINER_TABLE_REGIONS = TRAINER_DIALOG_REGIONS_2024
    TRAINER_DIALOG_AREA_ID = "trainer_dialog"

    # Build offset -> record mapping from both live and static corpora
    offset_to_record: dict[int, dict] = {}
    for rec in records:
        if rec.get("offset") is not None:
            offset_to_record[rec["offset"]] = rec
    for rec in static_corpus["records"]:
        if rec.get("offset") is not None:
            offset_to_record[rec["offset"]] = rec

    root = Path(__file__).resolve().parents[2]
    with open(ROM_PATH, "rb") as rom_file:
        rom_bytes = rom_file.read()

    trainer_records_tokenized = 0
    for region_start, region_end in TRAINER_TABLE_REGIONS:
        seen_targets = set()
        for off in range(region_start, region_end - 3):
            v = struct.unpack_from('<I', rom_bytes, off)[0]
            if (v & 0xFE000000) != 0x08000000:
                continue
            target = v - 0x08000000
            if target in seen_targets:
                continue
            seen_targets.add(target)
            rec = offset_to_record.get(target)
            if rec is None:
                continue
            text = rec.get("text", "")
            if not text:
                continue
            trainer_records_tokenized += 1
            try:
                tokens = mecab_lemmatize(text)
            except Exception:
                continue
            for lemma, pos, surface in tokens:
                if not (2 <= len(lemma) <= 5):
                    continue
                if not all(is_hangul(c) for c in lemma):
                    continue
                if is_phonetic_noise(lemma):
                    continue
                if is_kana_shape_token(lemma):
                    continue
                if pos == "noun" and len(lemma) >= 3 and has_no_batchim(lemma):
                    continue
                lemma_areas[lemma].add(TRAINER_DIALOG_AREA_ID)

    # Fourth pass: items obtained per area (from gItems table walk +
    # pokemart/giveitem opcode scan). For each (area, item_rec_id) entry
    # in item_obtain_index.json, tokenize the item description and add
    # the area to each lemma's set. Lemmas in canonical-area dialog keep
    # their canonical first_area (lower ordinal); item-only lemmas now
    # attribute to where the item is sold/given rather than rom_mined.
    ITEM_INDEX_PATH = Path(__file__).resolve().parent / "item_obtain_index.json"
    if ITEM_INDEX_PATH.exists():
        items_idx = json.loads(ITEM_INDEX_PATH.read_text())
        rec_id_to_record = {r["id"]: r for r in records}
        for r in static_corpus["records"]:
            rec_id_to_record.setdefault(r["id"], r)
        n_item_recs = 0
        for area, rec_ids in items_idx.get("area_to_item_rec_ids", {}).items():
            for rid in rec_ids:
                rec = rec_id_to_record.get(rid)
                if rec is None:
                    continue
                text = rec.get("text", "")
                if not text:
                    continue
                try:
                    tokens = mecab_lemmatize(text)
                except Exception:
                    continue
                for lemma, pos, surface in tokens:
                    if not (2 <= len(lemma) <= 5):
                        continue
                    if not all(is_hangul(c) for c in lemma):
                        continue
                    if is_phonetic_noise(lemma):
                        continue
                    if is_kana_shape_token(lemma):
                        continue
                    if pos == "noun" and len(lemma) >= 3 and has_no_batchim(lemma):
                        continue
                    lemma_areas[lemma].add(area)
                n_item_recs += 1
        print(f"  item-obtain attributions: {n_item_recs}")

    # Fifth pass: Pokedex entries per area (from gPokedexEntries +
    # gWildMonHeaders table walk). Each species' first-encounter area
    # gets its Pokedex description's lemmas tagged with that area.
    # Implements the canonical "first encountered in <route>" semantics.
    POKEDEX_INDEX_PATH = Path(__file__).resolve().parent / "pokedex_obtain_index.json"
    if POKEDEX_INDEX_PATH.exists():
        pokedex_idx = json.loads(POKEDEX_INDEX_PATH.read_text())
        rec_id_to_record_pdx = {r["id"]: r for r in records}
        for r in static_corpus["records"]:
            rec_id_to_record_pdx.setdefault(r["id"], r)
        n_pokedex_recs = 0
        for area, rec_ids in pokedex_idx.get("area_to_pokedex_rec_ids", {}).items():
            for rid in rec_ids:
                rec = rec_id_to_record_pdx.get(rid)
                if rec is None:
                    continue
                text = rec.get("text", "")
                if not text:
                    continue
                try:
                    tokens = mecab_lemmatize(text)
                except Exception:
                    continue
                for lemma, pos, surface in tokens:
                    if not (2 <= len(lemma) <= 5):
                        continue
                    if not all(is_hangul(c) for c in lemma):
                        continue
                    if is_phonetic_noise(lemma):
                        continue
                    if is_kana_shape_token(lemma):
                        continue
                    if pos == "noun" and len(lemma) >= 3 and has_no_batchim(lemma):
                        continue
                    lemma_areas[lemma].add(area)
                n_pokedex_recs += 1
        print(f"  pokedex-entry attributions: {n_pokedex_recs}")

    # Sixth pass: per-NPC trainer classes (gTrainers + objectEvent walk).
    # For each map's NPC trainer, parse trainerbattle opcode -> trainer_id,
    # look up gTrainers[trainer_id].class_id, get the Korean class name,
    # tag each lemma with that map's area. This is genuinely per-area
    # ("벌레잡이소년" attributes to pewter_city since the first Bug Catcher
    # the player meets is in Pewter), not the trainer_dialog sentinel.
    #
    # Falls back to the trainer_dialog sentinel for any class name whose
    # trainer NPCs weren't successfully mapped to a specific area.
    TRAINER_NPC_PATH = Path(__file__).resolve().parent / "trainer_npc_index.json"
    TRAINER_CLASS_PATH = Path(__file__).resolve().parent / "trainer_class_names.json"

    n_class_attributions = 0
    n_class_fallback = 0
    seen_class_names: set = set()
    if TRAINER_NPC_PATH.exists():
        npc_idx = json.loads(TRAINER_NPC_PATH.read_text())
        for area, class_names in npc_idx.get("area_to_trainer_class_names", {}).items():
            for name in class_names:
                seen_class_names.add(name)
                try:
                    tokens = mecab_lemmatize(name)
                except Exception:
                    continue
                for lemma, pos, surface in tokens:
                    if not (2 <= len(lemma) <= 5):
                        continue
                    if not all(is_hangul(c) for c in lemma):
                        continue
                    if is_phonetic_noise(lemma):
                        continue
                    if is_kana_shape_token(lemma):
                        continue
                    if pos == "noun" and len(lemma) >= 3 and has_no_batchim(lemma):
                        continue
                    lemma_areas[lemma].add(area)
                n_class_attributions += 1

    # Fallback: any class names not seen in the per-NPC walk -> trainer_dialog
    if TRAINER_CLASS_PATH.exists():
        tc = json.loads(TRAINER_CLASS_PATH.read_text())
        for idx, name in tc.get("translated_class_names", []):
            if name in seen_class_names:
                continue
            try:
                tokens = mecab_lemmatize(name)
            except Exception:
                continue
            for lemma, pos, surface in tokens:
                if not (2 <= len(lemma) <= 5):
                    continue
                if not all(is_hangul(c) for c in lemma):
                    continue
                if is_phonetic_noise(lemma):
                    continue
                if is_kana_shape_token(lemma):
                    continue
                if pos == "noun" and len(lemma) >= 3 and has_no_batchim(lemma):
                    continue
                lemma_areas[lemma].add(TRAINER_DIALOG_AREA_ID)
            n_class_fallback += 1
    print(f"  trainer-class per-NPC attributions: {n_class_attributions} (fallback: {n_class_fallback})")

    # Make sure the special area ids exist in area_ordinals for rank().
    area_ordinals[TRAINER_DIALOG_AREA_ID] = 51
    if STATIC_ONLY_AREA_ID not in area_ordinals:
        # Pull from areas.json (where rom_mined ordinal is 99).
        for a in load_json(AREAS_PATH)["areas"]:
            if a["id"] == STATIC_ONLY_AREA_ID:
                area_ordinals[a["id"]] = a["ordinal"]
                break

    # Build output
    lemmas_indexed = len(lemma_areas)
    all_area_ids = set()
    for areas in lemma_areas.values():
        all_area_ids.update(areas)
    areas_covered = len(all_area_ids)

    output = {
        "version": 1,
        "stats": {
            "records_tokenized": records_tokenized,
            "lemmas_indexed": lemmas_indexed,
            "areas_covered": areas_covered,
        },
        "lemmas": {},
    }

    def rank(a: str) -> int:
        # Treat negative or missing ordinals as last so canonical
        # story-progression areas always win first_area selection.
        o = area_ordinals.get(a, 999999)
        return o if o >= 0 else 999999

    for lemma, area_set in lemma_areas.items():
        sorted_areas = sorted(area_set, key=rank)
        first_area = sorted_areas[0] if sorted_areas else ""
        output["lemmas"][lemma] = {
            "first_area": first_area,
            "areas": sorted_areas,
            "rec_ids": lemma_rec_ids[lemma][:5],
        }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Summary
    print(f"live records tokenized: {records_tokenized}")
    print(f"static records tokenized: {static_records_tokenized}")
    print(f"trainer-table records tokenized: {trainer_records_tokenized}")
    print(f"distinct lemmas indexed: {lemmas_indexed}")
    top10 = sorted(lemma_areas.items(), key=lambda kv: len(kv[1]), reverse=True)[:10]
    for i, (lemma, areas) in enumerate(top10, 1):
        print(f"  {i:2d}. {lemma}  ({len(areas)} areas)")


if __name__ == "__main__":
    main()