#!/usr/bin/env python3
"""Suggest codepoint -> hangul mappings via n-gram triangulation.

The 2024 ROM's codepoint_map.json has only 534 of the ~1000 hangul
codepoints labeled (initial pass came from PokeAPI move/ability/species
name triangulation; see rom_swap/iterative_resolve.py). This script
extends coverage by mining the partially-decoded dialog corpus for
single-unknown contexts, then scoring candidate syllables against a
bigram/trigram language model built from the (clean, fully-decoded)
2010 ROM static corpus.

It does NOT auto-write codepoint_map.json — predictions are saved to
tools/moneo/codepoint_suggestions_2024.json for manual review. About
30% of suggestions are clearly correct (verifiable from semantic
context), 30% are clearly wrong (contexts don't make sense), 40% are
ambiguous. The accept policy below is conservative; widen `--margin`
or `--min-contexts` to surface more candidates.

Workflow:
  1. python3 tools/moneo/scan_rom_2024.py        # produces partial corpus
  2. python3 tools/moneo/triangulate_codepoints.py
  3. Manually review codepoint_suggestions_2024.json; copy verified
     entries into rom_swap/codepoint_map.json
  4. Re-run scan_rom_2024.py to refresh coverage
  5. Re-run downstream pipeline (walk_scripts_v2.py, attribute_existing_decks.py)

Usage:
    python3 tools/moneo/triangulate_codepoints.py
    python3 tools/moneo/triangulate_codepoints.py --margin 0.5 --min-contexts 5
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
ROOT = THIS_DIR.parents[1]

CORPUS_2024 = THIS_DIR / "corpus.ko.2024.json"
CORPUS_2010_STATIC = ROOT / "app/src/main/assets/moneo/corpus.ko.json"
CODEPOINT_MAP = THIS_DIR / "rom_swap/codepoint_map.json"
UNKNOWNS = THIS_DIR / "codepoint_unknowns_2024.json"
OUT_SUGGESTIONS = THIS_DIR / "codepoint_suggestions_2024.json"


def is_hangul(c: str) -> bool:
    return "가" <= c <= "힣"


def build_ngram_models(corpus_text: str):
    """Build (a, b) -> Counter[c] forward and (b, c) -> Counter[a] backward."""
    forward: dict[tuple[str, str], Counter] = defaultdict(Counter)
    backward: dict[tuple[str, str], Counter] = defaultdict(Counter)
    n = len(corpus_text)
    for i in range(n):
        ch = corpus_text[i]
        if not is_hangul(ch):
            continue
        if i >= 2 and is_hangul(corpus_text[i - 1]) and is_hangul(corpus_text[i - 2]):
            forward[(corpus_text[i - 2], corpus_text[i - 1])][ch] += 1
        if i + 2 < n and is_hangul(corpus_text[i + 1]) and is_hangul(corpus_text[i + 2]):
            backward[(corpus_text[i + 1], corpus_text[i + 2])][ch] += 1
    return forward, backward


def score_codepoint(cp_hex: str, records, forward, backward, mapped_syls: set[str]):
    """Sum forward + backward bigram weights across single-unknown contexts."""
    syl_scores: Counter = Counter()
    n_contexts = 0
    for r in records:
        text = r.get("text", "")
        markers = list(re.finditer(r"\[([0-9A-F]{4})\]", text))
        if len(markers) != 1:
            continue
        m = markers[0]
        if m.group(1) != cp_hex:
            continue
        pre = text[max(0, m.start() - 2):m.start()]
        post = text[m.end():m.end() + 2]
        pre_chars = [c for c in pre if is_hangul(c)]
        post_chars = [c for c in post if is_hangul(c)]
        if not pre_chars or not post_chars:
            continue
        n_contexts += 1
        if len(pre_chars) >= 2:
            for syl, count in forward.get((pre_chars[-2], pre_chars[-1]), {}).items():
                if syl in mapped_syls:
                    continue
                syl_scores[syl] += count * 2
        if len(post_chars) >= 2:
            for syl, count in backward.get((post_chars[0], post_chars[1]), {}).items():
                if syl in mapped_syls:
                    continue
                syl_scores[syl] += count * 2
    return syl_scores, n_contexts


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--margin", type=float, default=0.40,
                    help="min relative margin between top1 and top2 (default 0.40)")
    ap.add_argument("--min-contexts", type=int, default=3,
                    help="min single-unknown contexts to score (default 3)")
    ap.add_argument("--min-occurrences", type=int, default=5,
                    help="ignore unknowns occurring fewer than this many times (default 5)")
    args = ap.parse_args()

    static_records = json.loads(CORPUS_2010_STATIC.read_text())["records"]
    big_2010 = "\n".join(r.get("text", "") for r in static_records)
    print(f"2010 corpus: {len(static_records)} records, {len(big_2010):,} chars")
    forward, backward = build_ngram_models(big_2010)
    print(f"   forward bigrams: {len(forward):,}; backward bigrams: {len(backward):,}")

    corpus_2024 = json.loads(CORPUS_2024.read_text())
    records_2024 = corpus_2024["records"]
    print(f"2024 corpus: {len(records_2024)} records")

    cp_map = json.loads(CODEPOINT_MAP.read_text())
    existing_cps = {f"{int(k, 16):04X}" for k in cp_map}
    mapped_syls = set(cp_map.values())
    print(f"existing codepoint_map: {len(cp_map)} entries (covering {len(mapped_syls)} hangul)")

    unknowns = json.loads(UNKNOWNS.read_text())["unknowns"]

    suggestions = []
    skipped_low_freq = 0
    for u in unknowns:
        cp_hex = u["codepoint"].lstrip("0x").upper().zfill(4)
        if cp_hex in existing_cps:
            continue
        if u["occurrences"] < args.min_occurrences:
            skipped_low_freq += 1
            continue
        scores, n_ctx = score_codepoint(cp_hex, records_2024, forward, backward, mapped_syls)
        if not scores or n_ctx < args.min_contexts:
            continue
        top = scores.most_common(3)
        s1, n1 = top[0]
        s2, n2 = top[1] if len(top) > 1 else (None, 0)
        margin = (n1 - n2) / max(n1, 1)
        confidence_label = (
            "high" if margin >= args.margin and n_ctx >= args.min_contexts
            else "medium" if margin >= 0.25 and n_ctx >= args.min_contexts
            else "low"
        )
        suggestions.append({
            "codepoint": f"0x{cp_hex}",
            "predicted": s1,
            "confidence": confidence_label,
            "margin": round(margin, 2),
            "contexts": n_ctx,
            "occurrences": u["occurrences"],
            "runner_up": s2,
            "notes": "n-gram triangulation against 2010 corpus; manual review required",
        })

    suggestions.sort(key=lambda s: (
        {"high": 0, "medium": 1, "low": 2}[s["confidence"]],
        -s["margin"],
        -s["contexts"],
    ))

    OUT_SUGGESTIONS.write_text(json.dumps({
        "method": "ngram-triangulation-v1",
        "params": {
            "margin": args.margin,
            "min_contexts": args.min_contexts,
            "min_occurrences": args.min_occurrences,
        },
        "stats": {
            "suggestions_total": len(suggestions),
            "high_confidence": sum(1 for s in suggestions if s["confidence"] == "high"),
            "medium_confidence": sum(1 for s in suggestions if s["confidence"] == "medium"),
            "skipped_low_frequency": skipped_low_freq,
        },
        "suggestions": suggestions,
    }, ensure_ascii=False, indent=1))

    print(f"\nwrote {OUT_SUGGESTIONS}")
    print(f"   high confidence: {sum(1 for s in suggestions if s['confidence'] == 'high')}")
    print(f"   medium confidence: {sum(1 for s in suggestions if s['confidence'] == 'medium')}")
    print(f"   total suggestions: {len(suggestions)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
