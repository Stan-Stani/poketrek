#!/usr/bin/env python3
"""Annotate live-mined sentences with mapsec + area_id attribution.

For each sentence in sentences-ko-live-mined.json (source: rom-rec<id>),
looks up the rec_id in map_text_index.json's mapsec→rec_ids reverse
mapping to find which mapsec(s) reference it, then resolves each mapsec
to an area_id via mapsec_areas.json. The "first encountered" area is the
one with the lowest ordinal in areas.json among all hit areas.

Writes:
  - tools/moneo/sentences-ko-live-attributed.json (input + new fields)
  - tools/moneo/seed-vocab-ko-live-attributed.json (vocab + firstAreaEncountered)
"""
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SENTS_IN = ROOT / "tools/moneo/sentences-ko-live-mined.json"
VOCAB_IN = ROOT / "tools/moneo/seed-vocab-ko-live-mined.json"
MAP_INDEX = ROOT / "tools/moneo/map_text_index.json"
MAPSEC_AREAS = ROOT / "tools/moneo/mapsec_areas.json"
AREAS = ROOT / "app/src/main/assets/moneo/areas.json"

SENTS_OUT = ROOT / "tools/moneo/sentences-ko-live-attributed.json"
VOCAB_OUT = ROOT / "tools/moneo/seed-vocab-ko-live-attributed.json"
CORPUS_LIVE = ROOT / "tools/moneo/corpus.ko.live.json"


def main() -> int:
    sents = json.loads(SENTS_IN.read_text())
    vocab = json.loads(VOCAB_IN.read_text())
    map_idx = json.loads(MAP_INDEX.read_text())
    mapsec_areas = json.loads(MAPSEC_AREAS.read_text())["mapsecs"]
    areas = json.loads(AREAS.read_text())["areas"]
    area_ordinal = {a["id"]: a["ordinal"] for a in areas}
    # Areas not yet in areas.json (canyons, sevii islands, etc.) get a
    # fallback ordinal so they sort after the named areas. The user can
    # extend areas.json later.
    DEFAULT_ORDINAL = 500

    # Reverse map: rec_id -> set[mapsec]
    rec_to_mapsecs: dict[int, set[str]] = defaultdict(set)
    for ms, rids in map_idx["mapsec_to_rec_ids"].items():
        for rid in rids:
            rec_to_mapsecs[rid].add(ms)

    # Build overlap-fallback: many "fluent" records in the live corpus
    # are SUPERSETS of script-pointed records (the broader extraction
    # picked up script bytecode preceding the message text). When mining
    # picks the broader record, attribution misses. Fall back to: if the
    # source rec_id isn't mapsec-referenced, find ANY mapsec-referenced
    # rec_id whose text is contained in (or contains) the sentence text.
    live = json.loads(CORPUS_LIVE.read_text())
    referenced_recs = []
    for r in live["records"]:
        if r["id"] in rec_to_mapsecs:
            referenced_recs.append((r["id"], r["text"]))

    def rec_id_from_source(src: str) -> int | None:
        # source: "rom-rec1234" -> 1234
        if not src or not src.startswith("rom-rec"):
            return None
        try:
            return int(src.removeprefix("rom-rec"))
        except ValueError:
            return None

    def area_for_mapsec(ms: str) -> str | None:
        info = mapsec_areas.get(ms)
        if not info:
            return None
        return info.get("area_id")

    def first_area(mapsecs: set[str]) -> tuple[str | None, list[str]]:
        """Return (best_area_id, sorted_areas_seen)."""
        if not mapsecs:
            return None, []
        seen_areas: list[tuple[int, str, str]] = []
        for ms in mapsecs:
            aid = area_for_mapsec(ms)
            if aid is None:
                continue
            ord_ = area_ordinal.get(aid, DEFAULT_ORDINAL)
            seen_areas.append((ord_, aid, ms))
        if not seen_areas:
            return None, []
        seen_areas.sort()
        return seen_areas[0][1], [f"{ms}->{aid}" for _, aid, ms in seen_areas]

    def fallback_mapsecs_via_overlap(sentence: str) -> tuple[set[str], int | None]:
        """Find a mapsec-referenced rec whose text contains the sentence
        (or is contained in it). Returns (mapsecs, matched_rec_id)."""
        if len(sentence) < 4:
            return set(), None
        # Prefer EXACT containment first (sentence is in some referenced rec).
        for rid, text in referenced_recs:
            if sentence in text:
                return set(rec_to_mapsecs[rid]), rid
        # Fall back to fuzzy: take a 6-char prefix of the sentence and find
        # any referenced rec containing it. Tightens to lower false positives
        # by also requiring a 4-char suffix match anywhere in that rec.
        if len(sentence) < 8:
            return set(), None
        prefix, suffix = sentence[:6], sentence[-4:]
        for rid, text in referenced_recs:
            if prefix in text and suffix in text:
                return set(rec_to_mapsecs[rid]), rid
        return set(), None

    # Annotate sentences
    n_attributed = 0
    n_attributed_via_overlap = 0
    n_no_mapsec = 0
    n_no_area = 0
    for s in sents["entries"]:
        src = s.get("source")
        rid = rec_id_from_source(src)
        if rid is None:
            continue
        mapsecs = set(rec_to_mapsecs.get(rid, set()))
        if not mapsecs:
            # Fallback: search for the sentence text in any referenced rec.
            ms_set, matched_rid = fallback_mapsecs_via_overlap(s.get("korean", ""))
            if ms_set:
                mapsecs = ms_set
                s["sourceMapsecVia"] = f"rom-rec{matched_rid} (overlap)"
                n_attributed_via_overlap += 1
        s["mapsecs"] = sorted(mapsecs)
        if not mapsecs:
            n_no_mapsec += 1
            continue
        first, all_seen = first_area(mapsecs)
        s["mapsecAreaTrace"] = all_seen
        s["firstAreaEncountered"] = first
        if first:
            n_attributed += 1
        else:
            n_no_area += 1

    # Aggregate per-vocab: which areas does this lemma's sentences appear in?
    vocab_areas: dict[str, set[str]] = defaultdict(set)
    vocab_first: dict[str, tuple[int, str]] = {}  # vocab_id -> (ordinal, area_id)
    for s in sents["entries"]:
        vid = s.get("vocabId")
        first = s.get("firstAreaEncountered")
        if vid and first:
            vocab_areas[vid].add(first)
            ord_ = area_ordinal.get(first, DEFAULT_ORDINAL)
            cur = vocab_first.get(vid)
            if cur is None or ord_ < cur[0]:
                vocab_first[vid] = (ord_, first)

    # Annotate vocab entries. The vocab entries don't have an explicit
    # vocabId field — they're keyed by korean. The matching sentences use
    # vocabId = f"rom-mine-v2:{korean}". Cross-reference.
    source_tag = vocab.get("sourceTag", "rom-mine-v2")
    for v in vocab["entries"]:
        vid = f"{source_tag}:{v['korean']}"
        v["areasReferenced"] = sorted(vocab_areas.get(vid, set()))
        v["firstAreaEncountered"] = vocab_first.get(vid, (None, None))[1]

    # Stats
    print(f"sentences: {len(sents['entries'])} total")
    print(f"  with mapsec attribution: {n_attributed}")
    print(f"    of which recovered via text-overlap fallback: {n_attributed_via_overlap}")
    print(f"  no mapsec match (rec_id not in map_text_index): {n_no_mapsec}")
    print(f"  mapsec hit but no area_id mapped: {n_no_area}")
    print(f"vocab: {len(vocab['entries'])} total")
    print(f"  with firstAreaEncountered: {sum(1 for v in vocab['entries'] if v.get('firstAreaEncountered'))}")

    # Write
    sents["notes"] = sents.get("notes", "") + (
        " | Annotated with mapsecs + firstAreaEncountered via map_text_index.json "
        "and mapsec_areas.json. Some entries may have no mapsec match if their "
        "source rec_id is not script-referenced (e.g. battle text, system msgs)."
    )
    sents["sourceTag"] = sents.get("sourceTag", "") + "+mapattr"
    SENTS_OUT.write_text(json.dumps(sents, ensure_ascii=False, indent=2) + "\n")
    print(f"wrote {SENTS_OUT.relative_to(ROOT)}")

    vocab["notes"] = vocab.get("notes", "") + (
        " | Each entry tagged with areasReferenced (all areas its sentences "
        "appear in) and firstAreaEncountered (lowest-ordinal area)."
    )
    vocab["sourceTag"] = vocab.get("sourceTag", "") + "+mapattr"
    VOCAB_OUT.write_text(json.dumps(vocab, ensure_ascii=False, indent=2) + "\n")
    print(f"wrote {VOCAB_OUT.relative_to(ROOT)}")

    # Print a summary by area
    print("\nVocab counts by firstAreaEncountered:")
    by_area: dict[str | None, int] = defaultdict(int)
    for v in vocab["entries"]:
        by_area[v.get("firstAreaEncountered")] += 1
    for area, n in sorted(by_area.items(), key=lambda kv: -kv[1]):
        ord_ = area_ordinal.get(area, "?") if area else "—"
        print(f"  {str(area):>20}  (ord={ord_}):  {n}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
