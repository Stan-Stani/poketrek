#!/usr/bin/env python3
"""Analyse the gap structure between adjacent LIS anchors to decide
whether the atlas is dense in collation order (= we can fill gaps
without OCR) or sparse (= OCR is needed for ambiguous spots).

For each pair of adjacent LIS anchors (cp_a, syl_a) and (cp_b, syl_b)
where cp_a < cp_b and unicode(syl_a) < unicode(syl_b):
- cp_gap     = cp_b - cp_a - 1                   (intermediate atlas slots)
- uni_gap    = unicode(syl_b) - unicode(syl_a) - 1  (intermediate
                                                    syllables in
                                                    collation order)
- If cp_gap == uni_gap: dense. Every intermediate cp maps to the
  next syllable in collation order. We can fill blindly.
- If cp_gap < uni_gap: sparse. cp_gap of the uni_gap syllables are
  used; we need a way to decide which.
- If cp_gap > uni_gap: impossible if anchors are correct.

Output: distribution of gap shapes plus how many new mappings can be
auto-filled in the dense-case.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_jamo_atlas import decode_glyph

ROM_PATH = Path(__file__).resolve().parent / "leafgreen_J-K_2024.gba"
GBA_BASE = 0x08000000
ATLAS1_BASE = 0x08f18800
KNOWN_MAP_PATH = Path(__file__).resolve().parent / "codepoint_map.json"

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


def main():
    rom = ROM_PATH.read_bytes()
    raw = json.load(open(KNOWN_MAP_PATH))
    print(f"loaded {len(raw)} raw anchors")

    pil_cache = {}

    # Self-validate using PIL rendering (loose threshold to keep most).
    validated = []
    for cp_hex, syl in raw.items():
        cp = int(cp_hex, 16)
        icp = storage_to_internal(cp)
        glyph = render_rom_glyph(rom, icp)
        if glyph is None or glyph.sum() < 4:
            continue
        s = best_score(glyph, syl, pil_cache)
        if s >= 0.4:
            validated.append((cp, syl, ord(syl)))
    validated.sort()
    print(f"self-validated (PIL jaccard >= 0.4): {len(validated)}")

    # LIS by Unicode codepoint
    n = len(validated)
    dp = [1] * n
    prev = [-1] * n
    for i in range(n):
        for j in range(i):
            if validated[j][2] < validated[i][2] and dp[j] + 1 > dp[i]:
                dp[i] = dp[j] + 1
                prev[i] = j
    end = max(range(n), key=lambda i: dp[i])
    lis = []
    while end != -1:
        lis.append(validated[end])
        end = prev[end]
    lis.reverse()
    print(f"LIS in Unicode collation: {len(lis)}")

    # Analyse adjacent gaps
    dense_pairs = 0
    sparse_pairs = 0
    impossible_pairs = 0
    auto_fillable_cps = 0
    auto_fill_examples = []
    sparse_examples = []
    gap_shape_counter = Counter()  # (cp_gap, uni_gap)
    for i in range(1, len(lis)):
        cp_a, syl_a, uni_a = lis[i - 1]
        cp_b, syl_b, uni_b = lis[i]
        cp_gap = cp_b - cp_a - 1
        uni_gap = uni_b - uni_a - 1
        gap_shape_counter[(cp_gap, uni_gap)] += 1
        if cp_gap == uni_gap:
            dense_pairs += 1
            if cp_gap > 0:
                auto_fillable_cps += cp_gap
                if len(auto_fill_examples) < 6:
                    fills = []
                    for k in range(cp_gap):
                        fill_cp = cp_a + k + 1
                        fill_syl = chr(uni_a + k + 1)
                        fills.append(f"0x{fill_cp:04X}={fill_syl}")
                    auto_fill_examples.append({
                        "anchor_a": (f"0x{cp_a:04X}", syl_a),
                        "anchor_b": (f"0x{cp_b:04X}", syl_b),
                        "cp_gap": cp_gap,
                        "fills": fills,
                    })
        elif cp_gap < uni_gap:
            sparse_pairs += 1
            if len(sparse_examples) < 8:
                cands = [chr(uni_a + 1 + k) for k in range(uni_gap)]
                sparse_examples.append({
                    "anchor_a": (f"0x{cp_a:04X}", syl_a),
                    "anchor_b": (f"0x{cp_b:04X}", syl_b),
                    "cp_gap": cp_gap,
                    "uni_gap": uni_gap,
                    "candidates": cands,
                })
        else:
            impossible_pairs += 1
            if impossible_pairs <= 5:
                print(f"  impossible: {cp_a:04X} ({syl_a}) "
                      f"-> {cp_b:04X} ({syl_b})  cp_gap={cp_gap} > uni_gap={uni_gap}")

    print()
    print(f"adjacency analysis ({len(lis)-1} pairs):")
    print(f"  dense (cp_gap == uni_gap):     {dense_pairs}")
    print(f"  sparse (cp_gap < uni_gap):     {sparse_pairs}")
    print(f"  impossible (cp_gap > uni_gap): {impossible_pairs}")
    print()
    print(f"auto-fillable cps in dense gaps: {auto_fillable_cps}")
    print()
    print("most-common gap shapes (cp_gap, uni_gap):")
    for (cg, ug), n in gap_shape_counter.most_common(15):
        print(f"  ({cg:3d}, {ug:3d}): {n}")
    print()
    print("auto-fill examples (dense gaps):")
    for ex in auto_fill_examples:
        print(f"  {ex['anchor_a'][0]}={ex['anchor_a'][1]!r} ... "
              f"{ex['anchor_b'][0]}={ex['anchor_b'][1]!r}: cp_gap={ex['cp_gap']}")
        for f in ex['fills'][:8]:
            print(f"    {f}")
        if len(ex['fills']) > 8:
            print(f"    ... +{len(ex['fills']) - 8} more")
    print()
    print("sparse-gap examples (need OCR or other tiebreak):")
    for ex in sparse_examples:
        print(f"  {ex['anchor_a'][0]}={ex['anchor_a'][1]!r} ... "
              f"{ex['anchor_b'][0]}={ex['anchor_b'][1]!r}: "
              f"need to pick {ex['cp_gap']} of {ex['uni_gap']} candidates")
        print(f"    candidates: {''.join(ex['candidates'][:30])}"
              + ("..." if len(ex['candidates']) > 30 else ""))


if __name__ == "__main__":
    main()
