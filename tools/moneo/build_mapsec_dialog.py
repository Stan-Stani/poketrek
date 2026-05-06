#!/usr/bin/env python3
"""Build a per-mapsec dialog index for area-attribution.

Joins map_text_index.json (mapsec -> rec_id sets) with corpus.ko.live.json
(rec_id -> text). Output: tools/moneo/mapsec_dialog.json with each
mapsec's referenced rec_ids and their decoded text, sorted by rec_id
offset (which roughly corresponds to ROM ordering / story flow).

Also prints a human-readable summary so you can identify each mapsec
by its dialog content. Use that to hand-author the mapsec -> area_id
table; substring-matching TOPIK vocab against arbitrary record text is
too noisy to be reliable (e.g. "키" matches both "키" the noun and
every kana-romaji rendering containing the syllable).

Usage:
    python3 tools/moneo/build_mapsec_dialog.py             # write JSON
    python3 tools/moneo/build_mapsec_dialog.py --identify  # also print samples
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAP_TEXT_INDEX = ROOT / "tools/moneo/map_text_index.json"
CORPUS_LIVE = ROOT / "tools/moneo/corpus.ko.live.json"
OUT = ROOT / "tools/moneo/mapsec_dialog.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--identify", action="store_true",
                    help="print per-mapsec samples to help identify each area")
    ap.add_argument("--limit", type=int, default=8,
                    help="max sample lines per mapsec when --identify (default 8)")
    args = ap.parse_args()

    idx = json.loads(MAP_TEXT_INDEX.read_text())
    live = json.loads(CORPUS_LIVE.read_text())
    by_id = {r["id"]: r for r in live["records"]}

    mapsec_dialog = {}
    for ms_str, rids in idx["mapsec_to_rec_ids"].items():
        if not rids:
            continue
        # Sort rids by ROM offset (lower offset = earlier in ROM, often
        # earlier in story progression for dialog tables).
        recs = []
        for rid in rids:
            r = by_id.get(rid)
            if r is None:
                continue
            recs.append({
                "recId": rid,
                "offset": r["offset"],
                "text": r["text"],
                "hangul": r["hangul"],
            })
        recs.sort(key=lambda r: r["offset"])
        mapsec_dialog[ms_str] = recs

    out = {
        "version": 1,
        "rom": live.get("rom"),
        "note": ("Per-mapsec dialog index. Each mapsec's referenced "
                 "rec_ids resolved to text from corpus.ko.live.json. "
                 "Records sorted by ROM offset within each mapsec."),
        "stats": {
            "mapsecs_with_dialog": len(mapsec_dialog),
            "total_records": sum(len(v) for v in mapsec_dialog.values()),
            "distinct_records":
                len({r["recId"] for v in mapsec_dialog.values() for r in v}),
        },
        "mapsecs": mapsec_dialog,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(f"wrote {OUT} ({out['stats']['mapsecs_with_dialog']} mapsecs, "
          f"{out['stats']['distinct_records']:,} distinct records)")

    if args.identify:
        print("\n--- per-mapsec samples (translated dialog ranked first) ---")
        # Common Korean grammar markers that strongly indicate translated
        # dialog (vs kana-romaji noise). The kana-romaji uses single-syllable
        # phonetic Korean glyphs that don't form these patterns.
        TRANSLATED_MARKERS = (
            "이에요", "이지만", "입니다", "예요", "있어", "있다", "있는",
            "이에", "한다", "해요", "해서", "어요", "어서", "어!", "이?",
            "끼!", "끓!", "!\n", "?\n", "?", "!", "데요", "는걸",
            "을게", "은데", "이지", "이야", "어요", "지요", "다。",
        )

        def score(text: str) -> int:
            """Higher = more likely translated Korean."""
            s = 0
            if "{var:01}" in text:
                s += 5
            for m in TRANSLATED_MARKERS:
                if m in text:
                    s += 2
            # Penalize records dominated by single-syllable kana-romaji
            # (lots of repeated ' 누쿠' / ' 무스켄' / ' 케에' patterns).
            for noise in (" 누쿠", " 무스켄", " 케에", "하쿠", "키누쿠"):
                s -= text.count(noise)
            # Reward newline-broken dialog lines
            s += min(text.count("\n"), 5)
            return s

        for ms in sorted(mapsec_dialog):
            recs = mapsec_dialog[ms]
            ranked = sorted(recs, key=lambda r: (-score(r["text"]), -len(r["text"])))
            top = ranked[:args.limit]
            best_score = score(top[0]["text"]) if top else 0
            tag = "" if best_score >= 5 else " (low-translated-content)"
            print(f"\nmapsec {ms} ({len(recs)} records{tag}):")
            for r in top:
                text = r["text"].replace("{var:01}", "[player]")
                preview = text.replace("\n", " | ")[:140]
                print(f"  rec{r['recId']:5d} @ 0x{r['offset']:06X} (score={score(r['text']):+d}): {preview}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
