import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mine_vocab import (
    mecab_lemmatize,
    is_hangul,
    is_kana_shape_token,
    has_no_batchim,
    is_phonetic_noise,
    _MECAB,
)

CORPUS_PATH = Path(__file__).resolve().parent / "corpus.ko.live.json"
MAP_AREA_PATH = Path(__file__).resolve().parent / "map_area_index.json"
AREAS_PATH = Path(__file__).resolve().parent.parent / "app/src/main/assets/moneo/areas.json"
OUTPUT_PATH = Path(__file__).resolve().parent / "lemma_area_index.json"


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
    print(f"records tokenized: {records_tokenized}")
    print(f"distinct lemmas indexed: {lemmas_indexed}")
    top10 = sorted(lemma_areas.items(), key=lambda kv: len(kv[1]), reverse=True)[:10]
    for i, (lemma, areas) in enumerate(top10, 1):
        print(f"  {i:2d}. {lemma}  ({len(areas)} areas)")


if __name__ == "__main__":
    main()