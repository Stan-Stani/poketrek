#!/usr/bin/env python3
"""Monotonic constrained matching: between each pair of LIS anchors,
the K atlas slots must map to K of the N candidate syllables (in
collation order). Solve with a DP that maximises summed PIL OCR score
while preserving order.

Pipeline:
  1. Self-validate raw codepoint_map.json against PIL renders. Drop
     entries whose atlas glyph doesn't visually resemble the claimed
     syllable.
  2. Find LIS by Unicode codepoint -- the largest monotonic subset.
  3. For each adjacent LIS pair (cp_a, syl_a) -> (cp_b, syl_b):
       atlas slots = cps strictly between cp_a and cp_b
       candidates  = hangul syllables strictly between syl_a and syl_b
       score[i][j] = PIL OCR jaccard between atlas slot i and candidate j
       run a longest-increasing-monotonic-assignment DP to choose the
       K-of-N assignment that maximises total score.
  4. Accept assignments whose minimum slot score >= MIN_PER_SLOT, else
     leave that pair as unresolved.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_jamo_atlas import decode_glyph

ROM_PATH = Path(__file__).resolve().parent / "leafgreen_J-K_2024.gba"
GBA_BASE = 0x08000000
ATLAS1_BASE = 0x08f18800
KNOWN_MAP_PATH = Path(__file__).resolve().parent / "codepoint_map.json"
OUT = Path(__file__).resolve().parent / "codepoint_map.full.json"

HANGUL_LO = 0xAC00
HANGUL_HI = 0xD7A3
STORAGE_RANGES = [(0x3700, 0x40FF), (0x4100, 0x41FF)]

GLYPH_W = 16
GLYPH_H = 16

FONT_SPECS = [
    ("/System/Library/Fonts/AppleSDGothicNeo.ttc", 14),
    ("/System/Library/Fonts/AppleSDGothicNeo.ttc", 15),
    ("/System/Library/Fonts/AppleSDGothicNeo.ttc", 16),
    ("/System/Library/Fonts/Supplemental/AppleGothic.ttf", 16),
]
OFFSET_RANGE = [(dx, dy) for dx in range(-2, 3) for dy in range(-2, 3)]


def storage_to_internal(cp: int) -> int:
    return (((cp >> 8) & 0xff) - 0x35) << 8 | (cp & 0xff)


def render_rom_glyph(rom: bytes, internal_cp: int) -> np.ndarray | None:
    off = (ATLAS1_BASE - GBA_BASE) + internal_cp * 64
    if off + 64 > len(rom):
        return None
    src = rom[off:off + 64]
    im = decode_glyph(src, GLYPH_W, GLYPH_H)
    return (np.asarray(im, dtype=np.uint8) > 64).astype(np.uint8)


def render_pil_for_char(ch: str, cache: dict) -> list[np.ndarray]:
    if ch in cache:
        return cache[ch]
    masks = []
    for font_path, size in FONT_SPECS:
        try:
            font = ImageFont.truetype(font_path, size)
        except Exception:
            continue
        for dx, dy in OFFSET_RANGE:
            canvas = Image.new("L", (GLYPH_W, GLYPH_H), 0)
            d = ImageDraw.Draw(canvas)
            d.text((dx, dy), ch, fill=255, font=font)
            arr = (np.asarray(canvas, dtype=np.uint8) > 64).astype(np.uint8)
            if arr.sum() == 0:
                continue
            masks.append(arr)
    cache[ch] = masks
    return masks


def jaccard(a: np.ndarray, b: np.ndarray) -> float:
    inter = int(np.logical_and(a, b).sum())
    union = int(np.logical_or(a, b).sum())
    if union == 0:
        return 0.0
    return inter / union


def best_score(rom_glyph: np.ndarray, ch: str, cache: dict) -> float:
    masks = render_pil_for_char(ch, cache)
    if not masks:
        return 0.0
    return max(jaccard(rom_glyph, m) for m in masks)


def lis_by_unicode(anchors):
    n = len(anchors)
    if n == 0:
        return []
    dp = [1] * n
    prev = [-1] * n
    for i in range(n):
        for j in range(i):
            if anchors[j][2] < anchors[i][2] and dp[j] + 1 > dp[i]:
                dp[i] = dp[j] + 1
                prev[i] = j
    end = max(range(n), key=lambda i: dp[i])
    seq = []
    while end != -1:
        seq.append(anchors[end])
        end = prev[end]
    return list(reversed(seq))


def monotonic_assign(rom_slots, candidates, cache):
    """Given K atlas slots (binary masks) and N candidate syllables (chars),
    find the assignment slots[0..K-1] -> candidates[j_0 < j_1 < ... < j_{K-1}]
    that maximises sum of jaccard(slots[i], pil(candidates[j_i])).

    Returns (best_score_total, assigned_chars[K], per_slot_scores[K]).
    O(K * N) time, O(K * N) space.
    """
    K = len(rom_slots)
    N = len(candidates)
    if K == 0:
        return 0.0, [], []
    if K > N:
        # impossible: can't pick K monotonic from N < K
        return -1.0, [], []
    # score[i][j] = jaccard of rom_slots[i] vs PIL render of candidates[j]
    score = np.zeros((K, N), dtype=np.float32)
    for i, glyph in enumerate(rom_slots):
        for j, ch in enumerate(candidates):
            score[i][j] = best_score(glyph, ch, cache)
    # dp[i][j] = best total score using slots[0..i] with slot i mapped to
    # candidate index <= j (strict). dp_back[i][j] tracks the chosen j for slot i.
    NEG = -1e9
    dp = np.full((K, N), NEG, dtype=np.float32)
    back = np.full((K, N), -1, dtype=np.int32)
    # Base: slot 0 can map to any j; dp[0][j] = score[0][j]
    for j in range(N):
        dp[0][j] = score[0][j]
        back[0][j] = j
    # Make running max so dp[0][j] = max over j' <= j of score[0][j'] for downstream prefix max
    # Actually we'll use prefix-max separately.
    prefix_best = np.full(N, NEG, dtype=np.float32)
    prefix_best_idx = np.full(N, -1, dtype=np.int32)
    cur_best = NEG
    cur_best_idx = -1
    for j in range(N):
        if dp[0][j] > cur_best:
            cur_best = dp[0][j]
            cur_best_idx = j
        prefix_best[j] = cur_best
        prefix_best_idx[j] = cur_best_idx
    for i in range(1, K):
        new_prefix_best = np.full(N, NEG, dtype=np.float32)
        new_prefix_best_idx = np.full(N, -1, dtype=np.int32)
        cur_best = NEG
        cur_best_idx = -1
        for j in range(N):
            # Slot i maps to candidate j; previous slot must use prefix_best[j-1]
            if j == 0:
                continue
            prev_best = prefix_best[j - 1]
            if prev_best > NEG / 2:
                v = prev_best + score[i][j]
                if v > NEG / 2:
                    dp[i][j] = v
                    back[i][j] = prefix_best_idx[j - 1]
            if dp[i][j] > cur_best:
                cur_best = dp[i][j]
                cur_best_idx = j
            new_prefix_best[j] = cur_best
            new_prefix_best_idx[j] = cur_best_idx
        prefix_best = new_prefix_best
        prefix_best_idx = new_prefix_best_idx
    # Find argmax of dp[K-1][:]
    j_end = int(np.argmax(dp[K - 1]))
    if dp[K - 1][j_end] < NEG / 2:
        return -1.0, [], []
    total = float(dp[K - 1][j_end])
    # Trace back
    chosen_j = [0] * K
    j = j_end
    for i in range(K - 1, -1, -1):
        chosen_j[i] = j
        j = int(back[i][j])
    chars = [candidates[j] for j in chosen_j]
    per_slot = [float(score[i][chosen_j[i]]) for i in range(K)]
    return total, chars, per_slot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate-thresh", type=float, default=0.4)
    ap.add_argument("--min-per-slot", type=float, default=0.30)
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    rom = ROM_PATH.read_bytes()
    raw_known: dict[str, str] = json.load(open(KNOWN_MAP_PATH))
    print(f"loaded {len(raw_known)} raw anchors")

    pil_cache: dict[str, list[np.ndarray]] = {}

    # Stage 1: self-validate
    validated = []
    for cp_hex, syl in raw_known.items():
        cp = int(cp_hex, 16)
        icp = storage_to_internal(cp)
        glyph = render_rom_glyph(rom, icp)
        if glyph is None or glyph.sum() < 4:
            continue
        s = best_score(glyph, syl, pil_cache)
        if s >= args.validate_thresh:
            validated.append((cp, syl, ord(syl)))
    validated.sort()
    print(f"self-validated: {len(validated)}")

    # Stage 2: LIS
    lis = lis_by_unicode(validated)
    print(f"LIS in collation: {len(lis)}")

    # Stage 3: between each adjacent LIS pair, monotonic assignment.
    results = {}
    for cp, syl, _ in lis:
        results[f"{cp:04X}"] = {"match": syl, "source": "lis", "score": 1.0}

    # Pre-render every atlas slot we'll need.
    rom_slot_cache = {}
    def get_rom_slot(cp: int):
        if cp not in rom_slot_cache:
            icp = storage_to_internal(cp)
            g = render_rom_glyph(rom, icp)
            rom_slot_cache[cp] = g
        return rom_slot_cache[cp]

    for i in range(1, len(lis)):
        cp_a, syl_a, uni_a = lis[i - 1]
        cp_b, syl_b, uni_b = lis[i]
        # Atlas slots between cp_a+1 .. cp_b-1 (skipping ones with low-byte 0xFF)
        slot_cps = []
        slot_glyphs = []
        for cp in range(cp_a + 1, cp_b):
            if (cp & 0xFF) == 0xFF:
                continue
            g = get_rom_slot(cp)
            if g is None or g.sum() < 4:
                continue
            slot_cps.append(cp)
            slot_glyphs.append(g)
        if not slot_cps:
            continue
        # Candidate syllables strictly between in Unicode collation
        candidates = [chr(u) for u in range(uni_a + 1, uni_b)]
        if not candidates:
            continue
        K = len(slot_cps)
        N = len(candidates)
        if K > N:
            # Impossible -- skip; LIS already excluded these pairs but the
            # control-byte filter (0xFF) might rebalance.
            continue
        if K == N:
            # Dense gap: deterministic 1:1 mapping.
            for s_cp, ch in zip(slot_cps, candidates):
                results[f"{s_cp:04X}"] = {
                    "match": ch, "source": "dense", "score": 1.0,
                    "anchor_a": f"0x{cp_a:04X}={syl_a}",
                    "anchor_b": f"0x{cp_b:04X}={syl_b}",
                }
            continue
        # Sparse gap: monotonic assignment via DP.
        total, chars, per_slot = monotonic_assign(
            slot_glyphs, candidates, pil_cache)
        if not chars:
            continue
        # Accept only if every slot's score >= min-per-slot
        if min(per_slot) < args.min_per_slot:
            continue
        for s_cp, ch, sc in zip(slot_cps, chars, per_slot):
            results[f"{s_cp:04X}"] = {
                "match": ch, "source": "sparse_dp",
                "score": round(sc, 4),
                "anchor_a": f"0x{cp_a:04X}={syl_a}",
                "anchor_b": f"0x{cp_b:04X}={syl_b}",
                "candidates": N,
                "atlas_slots": K,
            }
        if args.debug:
            print(f"  pair 0x{cp_a:04X}-0x{cp_b:04X}: K={K} N={N} "
                  f"total={total:.2f}, min_slot={min(per_slot):.2f}, "
                  f"chars={''.join(chars[:8])}")

    print(f"\ntotal results: {len(results)}")
    print(f"  lis:        {sum(1 for r in results.values() if r['source']=='lis')}")
    print(f"  dense:      {sum(1 for r in results.values() if r['source']=='dense')}")
    print(f"  sparse_dp:  {sum(1 for r in results.values() if r['source']=='sparse_dp')}")

    # Validation: check known anchors that we DIDN'T include in LIS (but
    # were in the raw map and self-validated). Did we recover the right
    # syllable for them?
    raw_cp_to_syl = {int(k, 16): v for k, v in raw_known.items()}
    sanity_checked = 0
    sanity_correct = 0
    sanity_wrong = []
    for cp, syl, _ in validated:
        cp_hex = f"{cp:04X}"
        if cp_hex in results and results[cp_hex]["source"] != "lis":
            sanity_checked += 1
            if results[cp_hex]["match"] == syl:
                sanity_correct += 1
            else:
                sanity_wrong.append((cp_hex, syl, results[cp_hex]["match"],
                                     results[cp_hex]["score"]))
    print(f"\nsanity check (non-LIS validated anchors recovered):")
    print(f"  total: {sanity_checked}, correct: {sanity_correct}")
    print(f"  accuracy: {sanity_correct/max(1,sanity_checked):.1%}")
    if sanity_wrong[:10]:
        print(f"  some wrong (showing 10):")
        for cp_hex, exp, got, sc in sanity_wrong[:10]:
            print(f"    0x{cp_hex} expected={exp!r} got={got!r} score={sc}")

    OUT.write_text(json.dumps({
        "version": 4,
        "rom": "leafgreen_J-K_2024.gba",
        "method": "LIS + monotonic-assignment DP between LIS gaps "
                  "(PIL multi-font/offset jaccard scoring)",
        "stats": {
            "raw_anchors": len(raw_known),
            "validated_anchors": len(validated),
            "lis_anchors": len(lis),
            "final_map_size": len(results),
            "sanity_check_total": sanity_checked,
            "sanity_check_correct": sanity_correct,
            "sanity_accuracy": (sanity_correct / max(1, sanity_checked)),
        },
        "mappings": {cp: r["match"] for cp, r in results.items()},
        "details": results,
    }, indent=2, ensure_ascii=False))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
