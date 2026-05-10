#!/usr/bin/env python3
"""Combine mapsec_dialog.json + mapsec_areas.json + corpus into a
human-readable text-by-area output.

Layout:
  tools/moneo/text_by_area/<area_id>/<mapsec_hex>__<canonical>.md
    Each mapsec gets its own file under its area folder. Confidence
    labels travel with the mapsec, so a low-confidence mapsec assigned
    to area "pallet_town" is visibly separated from the high-confidence
    one. Records inside each file are sorted by ROM offset.

  tools/moneo/text_by_area/index.json
    Flat mapping of every record id to its (area_id, mapsec, offset),
    plus per-area / per-mapsec statistics.

A note on "·" and "[XXXX]":
  - `·` marks bytes outside the hangul codepoint range (control codes,
    name placeholders, ASCII like "/" or numbers — anything the
    decoder routes to a non-hangul slot).
  - `[XXXX]` marks an unmapped *hangul* codepoint -- we have its bytes
    in ROM but no syllable label yet. The atlas-based renderer can
    produce its glyph image (see render_jamo_atlas.py).
"""
from __future__ import annotations
import json, sys, re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent

MAPSEC_DIALOG = HERE / "mapsec_dialog.json"
MAPSEC_AREAS  = HERE / "mapsec_areas.json"
CORPUS_2024   = HERE / "corpus.ko.2024.json"
OUT_DIR       = HERE / "text_by_area"


def slugify(s: str) -> str:
    s = (s or "").strip().replace(" ", "_").replace("/", "_")
    s = re.sub(r"[^A-Za-z0-9_\-]+", "", s)
    return s or "unknown"


def main():
    mapsec_dialog = json.load(open(MAPSEC_DIALOG))
    mapsec_areas  = json.load(open(MAPSEC_AREAS))
    corpus        = json.load(open(CORPUS_2024))

    rec_by_id = {r["id"]: r for r in corpus["records"]}
    area_by_mapsec = mapsec_areas["mapsecs"]
    dialog_by_mapsec = mapsec_dialog["mapsecs"]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Wipe old per-area markdown so stale files don't linger.
    for p in OUT_DIR.glob("**/*.md"):
        p.unlink()
    for p in sorted(OUT_DIR.glob("*"), reverse=True):
        if p.is_dir():
            try: p.rmdir()
            except OSError: pass

    # Per-mapsec output: aggregate which area each mapsec belongs to.
    per_area_mapsecs: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    rec_to_area: dict[int, dict] = {}
    rec_to_mapsec: dict[int, list[str]] = defaultdict(list)
    total_records_emitted = 0
    distinct_records: set[int] = set()

    for mapsec_hex, recs in dialog_by_mapsec.items():
        info = area_by_mapsec.get(mapsec_hex, {}) or {}
        area_id = info.get("area_id") or f"unknown_mapsec_{mapsec_hex}"
        canonical = info.get("frlg_canonical") or ""
        confidence = info.get("confidence") or "unknown"

        recs_sorted = sorted(recs, key=lambda r: r["offset"])
        per_area_mapsecs[area_id].append((mapsec_hex, {
            "frlg_canonical": canonical,
            "confidence": confidence,
            "records": recs_sorted,
        }))

        for r in recs_sorted:
            rid = r["recId"]
            if rid not in rec_to_area:
                rec_to_area[rid] = {
                    "area_id": area_id,
                    "mapsec": mapsec_hex,
                    "frlg_canonical": canonical,
                    "confidence": confidence,
                    "offset": r["offset"],
                }
            rec_to_mapsec[rid].append(mapsec_hex)
            distinct_records.add(rid)
            total_records_emitted += 1

    # Write one markdown file per (area, mapsec).
    files_written = 0
    for area_id, mapsec_list in per_area_mapsecs.items():
        area_slug = slugify(area_id)
        area_dir = OUT_DIR / area_slug
        area_dir.mkdir(parents=True, exist_ok=True)
        for mapsec_hex, entry in sorted(mapsec_list):
            canonical = entry["frlg_canonical"]
            confidence = entry["confidence"]
            recs = entry["records"]

            cs = slugify(canonical) or f"mapsec_{mapsec_hex}"
            fname = f"{mapsec_hex}__{cs}.md"
            path = area_dir / fname
            with path.open("w") as f:
                f.write(f"# {area_id} — {mapsec_hex}\n\n")
                f.write(f"FRLG canonical: `{canonical}`  \n")
                f.write(f"Confidence: `{confidence}`  \n")
                f.write(f"Records: {len(recs)}\n\n")
                for r in recs:
                    f.write(f"## rec {r['recId']} (ROM 0x{r['offset']:06X})\n\n")
                    f.write("```\n")
                    f.write(r["text"])
                    f.write("\n```\n\n")
            files_written += 1

    # Master index
    index = {
        "version": 2,
        "rom": corpus["rom"],
        "encoding": corpus["encoding"],
        "stats": {
            "areas_with_text": len(per_area_mapsecs),
            "mapsecs_with_dialog": len(dialog_by_mapsec),
            "files_written": files_written,
            "distinct_records": len(distinct_records),
            "total_record_links": total_records_emitted,
        },
        "areas": {
            area: {
                "mapsec_count": len(ms),
                "mapsecs": [
                    {
                        "mapsec": mh,
                        "frlg_canonical": e["frlg_canonical"],
                        "confidence": e["confidence"],
                        "records": len(e["records"]),
                    } for mh, e in sorted(ms)
                ],
                "total_records": sum(len(e["records"]) for _, e in ms),
            } for area, ms in sorted(per_area_mapsecs.items())
        },
        "rec_to_area": {
            str(rid): {
                "area": info["area_id"],
                "mapsec": info["mapsec"],
                "frlg_canonical": info["frlg_canonical"],
                "confidence": info["confidence"],
                "offset_hex": f"0x{info['offset']:06X}",
                "all_mapsecs": rec_to_mapsec[rid],
            } for rid, info in rec_to_area.items()
        },
    }
    (OUT_DIR / "index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False))

    # Also emit an "unattributed" file with every corpus record that did
    # NOT get reached via map-script walking. These include trainer
    # dialogs, name-table entries, item/Pokedex descriptions, and system
    # strings — they're real text but the static walker can't pin them
    # to a specific in-game location.
    unattributed = [r for r in corpus["records"]
                    if r["id"] not in distinct_records
                    and r.get("hangul", 0) >= 1]
    unattributed.sort(key=lambda r: r["offset"])
    unatt_path = OUT_DIR / "unattributed.md"
    with unatt_path.open("w") as f:
        f.write(f"# Unattributed dialog records\n\n")
        f.write(f"Records in corpus.ko.2024.json with hangul content that "
                f"the map-script walker did not reach. Likely sources: "
                f"trainer rosters, name tables, item/Pokedex/system strings.\n\n"
                f"Records: {len(unattributed)}\n\n")
        for r in unattributed:
            f.write(f"## rec {r['id']} (ROM 0x{r['offset']:06X})\n\n")
            f.write("```\n")
            f.write(r["text"])
            f.write("\n```\n\n")
    print(f"wrote {len(unattributed)} unattributed records to {unatt_path}")

    print(f"wrote {files_written} markdown files across "
          f"{len(per_area_mapsecs)} areas to {OUT_DIR}")
    print(f"distinct dialog records linked: {len(distinct_records)}")
    print()
    print("areas (sorted by record count desc):")
    rows = [(a, sum(len(e['records']) for _, e in ms))
            for a, ms in per_area_mapsecs.items()]
    for a, n in sorted(rows, key=lambda x: -x[1]):
        print(f"  {a:30s}  {n:5d} records  "
              f"(mapsecs: {len(per_area_mapsecs[a])})")


if __name__ == "__main__":
    main()
