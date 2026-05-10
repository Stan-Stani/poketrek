#!/usr/bin/env python3
"""Brute-force scan the patched region (0xD00000..0xFFFFFF) for LZ77 blocks.

For every 4-byte-aligned offset where byte[0]==0x10, attempt LZ77 decompress.
If it succeeds (no out-of-bounds, no over-the-cap), record the result and
score for "looks like hangul font tile data".

Hangul-font heuristics:
- Output size in [0x4000, 0x40000] (16 KB to 256 KB)
- Tile density mid-range (15-65% non-zero per 32-byte tile, 4bpp)
- High variance across tiles (real glyphs vary; padding tiles don't)
- Repeating 16x16-glyph shape: top-half of consecutive 64-byte glyphs
  shares the initial consonant, so first 16 bytes of glyph N and N+1
  often match for sequences of >5 glyphs

Output: a CSV with all valid LZ77 blocks ranked by hangul-likeness score.
"""
from __future__ import annotations
from pathlib import Path
import struct

ROM = Path(__file__).resolve().parent / "leafgreen_J-K_2024.gba"
OUT = Path(__file__).resolve().parent / "patched_lz77_blocks.csv"
GBA_BASE = 0x08000000
SCAN_LO = 0xD00000
SCAN_HI = 0x1000000


def lz77_decompress(data: bytes, offset: int, max_size: int = 0x80000) -> bytes | None:
    if offset + 4 > len(data) or data[offset] != 0x10:
        return None
    size = data[offset + 1] | (data[offset + 2] << 8) | (data[offset + 3] << 16)
    if size == 0 or size > max_size:
        return None
    src = offset + 4
    out = bytearray()
    try:
        while len(out) < size:
            if src >= len(data):
                return None
            flags = data[src]; src += 1
            for bit in range(8):
                if len(out) >= size:
                    break
                if (flags & (0x80 >> bit)) == 0:
                    if src >= len(data):
                        return None
                    out.append(data[src]); src += 1
                else:
                    if src + 1 >= len(data):
                        return None
                    hi = data[src]; lo = data[src + 1]; src += 2
                    length = (hi >> 4) + 3
                    disp = ((hi & 0x0F) << 8) | lo
                    pos = len(out) - disp - 1
                    if pos < 0:
                        return None
                    for _ in range(length):
                        out.append(out[pos]); pos += 1
    except Exception:
        return None
    return bytes(out[:size])


def score_tile_data(b: bytes) -> dict:
    """Score how 'tile-like' and 'hangul-font-like' the data is."""
    if len(b) < 64:
        return {"tile_count": 0, "score": 0}
    n_tiles = len(b) // 32  # 4bpp 8x8 tile = 32 bytes
    densities = []
    for i in range(n_tiles):
        tile = b[i*32:(i+1)*32]
        densities.append(sum(1 for x in tile if x != 0) / 32)
    mean = sum(densities) / n_tiles
    var = sum((d - mean) ** 2 for d in densities) / n_tiles
    std = var ** 0.5

    # Glyph-pair similarity: assume 64-byte glyphs (4 8x8 tiles each, 16x16),
    # check if the top-half of consecutive glyphs shares prefix bytes.
    n_glyphs = len(b) // 64
    glyph_pair_matches = 0
    for i in range(n_glyphs - 1):
        g1 = b[i*64:i*64+16]
        g2 = b[(i+1)*64:(i+1)*64+16]
        if g1 != g2 and sum(1 for a, c in zip(g1, g2) if a == c) >= 12:
            glyph_pair_matches += 1
    pair_ratio = glyph_pair_matches / max(1, n_glyphs - 1)

    # Hangul-likeness:
    # - density in mid-range (real glyphs, not solid fill or empty)
    # - moderate-to-high std (varied tiles)
    # - some glyph-pair similarity (initial-consonant repeat)
    score = 0
    if 0.10 < mean < 0.65:
        score += 30
    if std > 0.10:
        score += 30
    if pair_ratio > 0.10:
        score += 40
    return {
        "tile_count": n_tiles,
        "glyphs_64": n_glyphs,
        "mean_density": round(mean, 3),
        "std_density": round(std, 3),
        "glyph_pair_match_ratio": round(pair_ratio, 3),
        "score": score,
    }


def main():
    data = ROM.read_bytes()
    print(f"Scanning {ROM.name} from {SCAN_LO:#x} to {SCAN_HI:#x}")
    candidates = []
    for off in range(SCAN_LO, SCAN_HI, 4):
        if data[off] != 0x10:
            continue
        out = lz77_decompress(data, off)
        if out is None or len(out) < 0x100:
            continue
        s = score_tile_data(out)
        if s["score"] < 30:
            continue
        candidates.append({
            "file_off": off,
            "gba_addr": off + GBA_BASE,
            "usize": len(out),
            **s,
        })

    candidates.sort(key=lambda c: -c["score"])
    print(f"Found {len(candidates)} viable LZ77 blocks (score ≥ 30)")
    print()
    print(f"{'rank':>4} {'gba':>10} {'usize':>7} {'tiles':>5} {'glyphs':>6} "
          f"{'dens':>5} {'std':>5} {'pair%':>5} {'score':>5}")
    for i, c in enumerate(candidates[:40]):
        print(f"{i+1:>4} {c['gba_addr']:>10x} {c['usize']:>7} {c['tile_count']:>5} "
              f"{c['glyphs_64']:>6} {c['mean_density']:>5} {c['std_density']:>5} "
              f"{c['glyph_pair_match_ratio']:>5} {c['score']:>5}")

    with OUT.open("w") as f:
        f.write("rank,gba_addr,file_off,usize,tile_count,glyphs_64,mean_density,std_density,pair_ratio,score\n")
        for i, c in enumerate(candidates):
            f.write(f"{i+1},{c['gba_addr']:#x},{c['file_off']:#x},{c['usize']},{c['tile_count']},"
                    f"{c['glyphs_64']},{c['mean_density']},{c['std_density']},"
                    f"{c['glyph_pair_match_ratio']},{c['score']}\n")
    print(f"\nFull dump → {OUT}")


if __name__ == "__main__":
    main()
