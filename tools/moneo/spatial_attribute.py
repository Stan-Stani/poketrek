#!/usr/bin/env python3
"""Spatial fallback attribution: assign every unattributed live-corpus
record to the area of the nearest attributed record by ROM offset.

The Korean LeafGreen ROM lays out text records contiguously per
topic/area: adjacent records are typically in the same script context.
For records that map-walking can't reach (extractor over-emitted overlap
variants, records referenced via global tables, etc.), the nearest-
neighbor heuristic recovers a sensible area assignment without false
attribution.

Output: tools/moneo/spatial_rec_areas.json
"""
from __future__ import annotations
import argparse
import bisect
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS_LIVE = Path(__file__).resolve().parent / "corpus.ko.live.json"
MAP_AREA = Path(__file__).resolve().parent / "map_area_index.json"
AREAS = ROOT / "app/src/main/assets/moneo/areas.json"
OUT = Path(__file__).resolve().parent / "spatial_rec_areas.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-distance", type=int, default=4096,
                    help="Max ROM-offset distance to nearest attributed record.")
    args = ap.parse_args()

    live = json.loads(CORPUS_LIVE.read_text())
    mai = json.loads(MAP_AREA.read_text())
    areas_list = json.loads(AREAS.read_text())["areas"]
    area_ordinal = {a["id"]: a["ordinal"] for a in areas_list}

    def rank(a: str) -> int:
        o = area_ordinal.get(a, 999999)
        return o if o >= 0 else 999999

    # rec_id -> best area (lowest-ordinal among areas that contain it)
    rec_to_best_area: dict[int, str] = {}
    for aid, info in mai.get("resolved_areas", {}).items():
        for rid in info.get("recIds", []):
            cur = rec_to_best_area.get(rid)
            if cur is None or rank(aid) < rank(cur):
                rec_to_best_area[rid] = aid

    # Build offset -> rec_id and sorted attributed-offset list
    rec_to_offset: dict[int, int] = {}
    for r in live["records"]:
        if r.get("offset") is not None:
            rec_to_offset[r["id"]] = r["offset"]

    attributed_offsets: list[tuple[int, str]] = []
    for rid, area in rec_to_best_area.items():
        off = rec_to_offset.get(rid)
        if off is not None:
            attributed_offsets.append((off, area))
    attributed_offsets.sort()
    sorted_offs = [off for off, _ in attributed_offsets]
    sorted_areas = [a for _, a in attributed_offsets]

    spatial_attr: dict[str, str] = {}
    distances: list[int] = []
    n_total = len(live["records"])
    n_already = 0
    n_too_far = 0

    for r in live["records"]:
        rid = r["id"]
        off = r.get("offset")
        if off is None:
            continue
        if rid in rec_to_best_area:
            n_already += 1
            continue
        # Binary-search for nearest attributed offset
        i = bisect.bisect_left(sorted_offs, off)
        candidates = []
        if i < len(sorted_offs):
            candidates.append((sorted_offs[i] - off, sorted_offs[i], sorted_areas[i]))
        if i > 0:
            candidates.append((off - sorted_offs[i - 1], sorted_offs[i - 1], sorted_areas[i - 1]))
        if not candidates:
            continue
        candidates.sort()  # nearest first; ties prefer earlier offset
        dist, near_off, near_area = candidates[0]
        if dist > args.max_distance:
            n_too_far += 1
            continue
        spatial_attr[str(rid)] = near_area
        distances.append(dist)

    out = {
        "version": 1,
        "stats": {
            "live_records_total": n_total,
            "already_attributed": n_already,
            "spatial_attributed": len(spatial_attr),
            "still_unattributed": n_total - n_already - len(spatial_attr),
            "median_distance": sorted(distances)[len(distances) // 2] if distances else 0,
        },
        "rec_to_area": spatial_attr,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")

    print(f"live records:          {n_total:,}")
    print(f"  already attributed:  {n_already:,}")
    print(f"  spatial attributed:  {len(spatial_attr):,}")
    print(f"  still unattributed:  {n_total - n_already - len(spatial_attr):,}")
    print(f"  median distance:     {out['stats']['median_distance']} bytes")

    by_area = Counter(spatial_attr.values())
    print("\nTop 10 spatial-attribution areas:")
    for area, n in by_area.most_common(10):
        print(f"  {area}: {n}")

    print(f"\nWrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
