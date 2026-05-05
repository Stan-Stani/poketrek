#!/usr/bin/env python3
"""Pair (page, idx) tokens captured at the glyph-render breakpoint with
VRAM tile-group fingerprints captured shortly after, to derive a
(page, idx) -> fingerprint -> Hangul map.

Inputs
------
capture.json: produced by tools/moneo/mgba_capture/mgba_capture
  {"tokens": [{frame, page, idx, ...}, ...],
   "groups": [{frame, line, fps:[fp0..fp3], tiles:[..]}, ...]}
ko_charmap.json: {fingerprint_hex: "글"}  (verified subset)
charmap-v1.json (optional): {"PAGE:IDX_HEX": {"ch": "글", "score": float}}

Strategy
--------
For each token at frame F we look at the set of fingerprints present in
group snapshots in the post-window [F+1, F+POST] minus those already
present in the pre-window [F-PRE, F-1].  Those are "new" fingerprints
caused (most likely) by this and any sibling tokens fired in the same
batch.

Then for each (page, idx) we intersect the new-sets across all of its
occurrences.  After enough frames the intersection collapses to one
fingerprint (the unique glyph this (page, idx) renders).

Usage
-----
python3 tools/moneo/pair_tokens.py \
    --capture .moneo-artifacts/capture-long.json \
    --ko-charmap app/src/main/assets/moneo/ko_charmap.json \
    --v1-charmap .moneo-artifacts/charmap-v1.json \
    --out .moneo-artifacts/pair-map.json
"""
from __future__ import annotations

import argparse
import json
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple


def load_capture(path: Path) -> Tuple[list, list]:
    data = json.loads(path.read_text())
    return data.get("tokens", []), data.get("groups", [])


def build_frame_index(groups: list) -> Tuple[List[int], List[Set[str]]]:
    """Return (sorted unique frames, per-frame fp-set) over group snapshots."""
    by_frame: Dict[int, Set[str]] = defaultdict(set)
    for g in groups:
        f = g["frame"]
        for fp in g.get("fps", []):
            if fp:
                by_frame[f].add(fp)
    frames = sorted(by_frame)
    sets = [by_frame[f] for f in frames]
    return frames, sets


def fps_in_window(frames: List[int], sets: List[Set[str]], lo: int, hi: int) -> Set[str]:
    if not frames or lo > hi:
        return set()
    i = bisect_left(frames, lo)
    j = bisect_right(frames, hi)
    out: Set[str] = set()
    for k in range(i, j):
        out |= sets[k]
    return out


def pair(tokens: list, groups: list, pre: int, post: int) -> Tuple[Dict[Tuple[int, int], Counter], Counter]:
    """Score (page, idx) -> Counter[fp] using a token-frequency-normalized
    pointwise mutual information (PMI) heuristic.

    For each token at frame F we add +1 to fp_freq[key][fp] for every fp
    appearing in the post-window [F+1, F+post].  We also count how often
    each fp appears in any post-window (global_freq[fp]).  The score for
    (key, fp) is then fp_freq[key][fp] / global_freq[fp]: a glyph that
    appears proportionally more often after this (p,i) than after random
    tokens scores high.
    """
    frames, sets = build_frame_index(groups)
    occurrences: Counter = Counter()
    fp_freq: Dict[Tuple[int, int], Counter] = defaultdict(Counter)
    global_freq: Counter = Counter()

    for t in tokens:
        key = (int(t["page"]), int(t["idx"]))
        f = int(t["frame"])
        after = fps_in_window(frames, sets, f + 1, f + post)
        occurrences[key] += 1
        for fp in after:
            fp_freq[key][fp] += 1
            global_freq[fp] += 1

    total_tokens = max(1, sum(occurrences.values()))
    scored: Dict[Tuple[int, int], Counter] = {}
    for key, c in fp_freq.items():
        n = occurrences[key]
        # PMI-like: ratio of conditional freq to marginal freq.  High when
        # fp shows up especially often after this token relative to its
        # baseline rate.  Multiply by log(n) to favour well-attested keys.
        s: Counter = Counter()
        for fp, cnt in c.items():
            cond = cnt / n
            marg = global_freq[fp] / total_tokens
            if marg <= 0:
                continue
            ratio = cond / marg
            # Use 4 decimals scaled to int for stable Counter ordering.
            s[fp] = round(ratio * cnt, 4)
        scored[key] = s
    return scored, occurrences


def load_json(path: Path | None) -> dict:
    if not path:
        return {}
    return json.loads(Path(path).read_text())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture", required=True, type=Path)
    ap.add_argument("--ko-charmap", type=Path, default=None,
                    help="JSON map fingerprint_hex -> Hangul.")
    ap.add_argument("--v1-charmap", type=Path, default=None,
                    help="JSON map PAGE:IDX_HEX -> {ch, score}.")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--pre", type=int, default=60)
    ap.add_argument("--post", type=int, default=60)
    args = ap.parse_args()

    tokens, groups = load_capture(args.capture)
    print(f"[pair] tokens={len(tokens)} groups={len(groups)}")

    scored, occ = pair(tokens, groups, args.pre, args.post)
    print(f"[pair] resolved keys={len(scored)} (unique tokens seen={len(occ)})")

    ko_map: Dict[str, str] = load_json(args.ko_charmap)
    v1_map: Dict[str, dict] = load_json(args.v1_charmap)

    out_entries: Dict[str, dict] = {}
    fp_resolved = 0
    cross_check = 0
    for (page, idx), c in scored.items():
        if not c:
            continue
        top_fp, top_n = c.most_common(1)[0]
        page_hex = f"{page:X}"
        idx_hex = f"{idx:02X}"
        key = f"{page_hex}:{idx_hex}"
        ch_from_fp = ko_map.get(top_fp)
        v1 = v1_map.get(key) or v1_map.get(f"{page}:{idx_hex}")
        ch_from_v1 = v1.get("ch") if v1 else None
        v1_score = v1.get("score") if v1 else None
        if ch_from_fp:
            fp_resolved += 1
        if ch_from_fp and ch_from_v1 and ch_from_fp == ch_from_v1:
            cross_check += 1
        out_entries[key] = {
            "page": page,
            "idx": idx,
            "occurrences": occ[(page, idx)],
            "candidates": c.most_common(8),
            "top_fp": top_fp,
            "top_fp_n": top_n,
            "ch_from_fp": ch_from_fp,
            "ch_from_v1": ch_from_v1,
            "v1_score": v1_score,
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_entries, ensure_ascii=False, indent=2))
    print(f"[pair] wrote {args.out} ({len(out_entries)} entries)")
    print(f"[pair] fp-resolved (ko_charmap match)= {fp_resolved}")
    print(f"[pair] cross-check (fp == v1)       = {cross_check}")


if __name__ == "__main__":
    main()
