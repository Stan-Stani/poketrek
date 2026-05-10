#!/usr/bin/env python3
"""OCR atlas glyphs using:
  1. Self-validation of the existing codepoint_map.json against a PIL
     hangul render -- keep only anchors whose atlas glyph passes a
     similarity threshold to the PIL render of their claimed syllable.
  2. Among the validated anchors, keep the longest increasing
     subsequence in Unicode collation order (sorted by storage cp).
  3. For each unknown cp, constrain the candidate set to syllables
     bracketed by the surrounding LIS anchors and pick the candidate
     with best PIL/atlas similarity.

Output: codepoint_map.full.json
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


def render_pil_for_char(ch: str) -> list[np.ndarray]:
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
    return masks


def jaccard(a: np.ndarray, b: np.ndarray) -> float:
    inter = int(np.logical_and(a, b).sum())
    union = int(np.logical_or(a, b).sum())
    if union == 0:
        return 0.0
    return inter / union


def best_score(rom_glyph: np.ndarray, ch: str,
               cache: dict[str, list[np.ndarray]]) -> float:
    if ch not in cache:
        cache[ch] = render_pil_for_char(ch)
    masks = cache[ch]
    if not masks:
        return 0.0
    return max(jaccard(rom_glyph, m) for m in masks)


def lis_by_unicode(anchors: list[tuple[int, str, int]]) -> list[tuple[int, str, int]]:
    """Longest increasing subsequence of (cp, syl, uni) sorted by cp,
    increasing in `uni`."""
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate-thresh", type=float, default=0.4,
                    help="self-validation: anchor's atlas glyph must score "
                         ">= this against PIL render of claimed syllable")
    ap.add_argument("--match-thresh", type=float, default=0.4,
                    help="OCR: accept new mapping if score >= this")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    rom = ROM_PATH.read_bytes()
    raw_known: dict[str, str] = json.load(open(KNOWN_MAP_PATH))
    print(f"loaded {len(raw_known)} known anchors")

    pil_cache: dict[str, list[np.ndarray]] = {}

    # Stage 1: self-validate
    validated: list[tuple[int, str, int]] = []
    rejected_anchors: list[tuple[int, str, float]] = []
    for cp_hex, syl in raw_known.items():
        cp = int(cp_hex, 16)
        icp = storage_to_internal(cp)
        glyph = render_rom_glyph(rom, icp)
        if glyph is None or glyph.sum() < 4:
            rejected_anchors.append((cp, syl, -1.0))
            continue
        s = best_score(glyph, syl, pil_cache)
        if s >= args.validate_thresh:
            validated.append((cp, syl, ord(syl)))
        else:
            rejected_anchors.append((cp, syl, s))
    validated.sort()
    print(f"self-validated anchors: {len(validated)} / {len(raw_known)}")
    print(f"rejected anchors (low PIL similarity): {len(rejected_anchors)}")

    # Stage 2: LIS
    lis = lis_by_unicode(validated)
    print(f"longest increasing subsequence in Unicode collation: {len(lis)}")

    # Stage 3: constrained OCR for unknowns
    storage_cps_to_ocr = []
    for lo, hi in STORAGE_RANGES:
        for cp in range(lo, hi + 1):
            if (cp & 0xFF) == 0xFF:
                continue
            storage_cps_to_ocr.append(cp)

    # For each cp in storage range (including known), determine bracketing
    # LIS anchors and OCR if beyond LIS.
    lis_cps = {a[0] for a in lis}
    results = {}
    for cp in storage_cps_to_ocr:
        cp_hex = f"{cp:04X}"
        if cp in lis_cps:
            # already verified
            for a_cp, a_syl, a_uni in lis:
                if a_cp == cp:
                    results[cp_hex] = {"match": a_syl, "score": 1.0,
                                       "source": "lis"}
                    break
            continue
        icp = storage_to_internal(cp)
        glyph = render_rom_glyph(rom, icp)
        if glyph is None or glyph.sum() < 4:
            continue
        # Find bracket within LIS
        prev = None
        next_ = None
        for a_cp, a_syl, a_uni in lis:
            if a_cp < cp:
                prev = (a_cp, a_syl, a_uni)
            elif a_cp > cp:
                next_ = (a_cp, a_syl, a_uni)
                break
        lo_uni = (prev[2] + 1) if prev else HANGUL_LO
        hi_uni = (next_[2] - 1) if next_ else HANGUL_HI
        if hi_uni < lo_uni:
            continue
        candidates = [chr(u) for u in range(lo_uni, hi_uni + 1)]
        best_ch, best_s = None, -1.0
        for ch in candidates:
            s = best_score(glyph, ch, pil_cache)
            if s > best_s:
                best_s = s
                best_ch = ch
        if best_ch is not None and best_s >= args.match_thresh:
            results[cp_hex] = {
                "match": best_ch,
                "score": round(best_s, 4),
                "candidates": len(candidates),
                "source": "ocr",
                "lo_uni": lo_uni,
                "hi_uni": hi_uni,
            }

    print(f"\nfinal map: {len(results)} entries")
    print(f"  from LIS anchors: {sum(1 for r in results.values() if r['source']=='lis')}")
    print(f"  from OCR:         {sum(1 for r in results.values() if r['source']=='ocr')}")

    OUT.write_text(json.dumps({
        "version": 3,
        "rom": "leafgreen_J-K_2024.gba",
        "method": "self-validated 539 anchors -> LIS by Unicode -> "
                  "constrained PIL/atlas jaccard OCR",
        "stats": {
            "raw_anchors": len(raw_known),
            "validated_anchors": len(validated),
            "lis_anchors": len(lis),
            "final_map_size": len(results),
            "ocr_count": sum(1 for r in results.values() if r['source']=='ocr'),
        },
        "mappings": {cp: r["match"] for cp, r in results.items()},
        "details": results,
    }, indent=2, ensure_ascii=False))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
