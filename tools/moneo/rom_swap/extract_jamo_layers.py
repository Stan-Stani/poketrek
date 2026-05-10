#!/usr/bin/env python3
"""Decompose 2024 dialog tiles into jamo layers.

The 2024 patch's renderer composes each hangul syllable from 2 jamo
bitmaps stored at independent palette indices (2 and 3) within the same
4bpp tile in EWRAM. Color 2 == one jamo, color 3 == another. The two
layers are NOT shadow-shifted variants of each other — they are
independent shapes (verified empirically: m2 ⊆ m3 in 0/146 tiles, and
m2 == shifted(m3, dx, dy) in only 5 of 146 with shift (-1, 0); the rest
have no shift relationship).

Run after `drive_to_dialog.lua` has populated /tmp/poketrek_drive/ with
a dialog-frame snapshot. Outputs per-layer 1bpp masks, and saves visual
PNGs of each layer extracted from the EWRAM glyph cache region.

The next step (currently unsolved) is to find the storage format of
the jamo source bitmaps in ROM. They are not byte-equal to any 1bpp/
2bpp/4bpp encoding tried — likely either bit-packed (variable-stride),
algorithmically generated, or stored in a non-pixel format that the
renderer interprets to draw strokes.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter
import argparse

EWRAM_DUMP = "/tmp/poketrek_drive/010_f00630_ewram.bin"
GLYPH_CACHE_LO = 0x7000
GLYPH_CACHE_HI = 0x9000


def color_mask(tile32: bytes, color: int) -> bytes:
    """Return 8-byte 1bpp mask of pixels in `tile32` whose nibble == `color`."""
    out = bytearray(8)
    for y in range(8):
        bits = 0
        for x in range(0, 8, 2):
            b = tile32[y * 4 + x // 2]
            if (b & 0x0F) == color:
                bits |= 1 << x
            if ((b >> 4) & 0x0F) == color:
                bits |= 1 << (x + 1)
        out[y] = bits
    return bytes(out)


def shift_mask(m: bytes, dx: int, dy: int) -> bytes:
    out = bytearray(8)
    for y in range(8):
        sy = y - dy
        if 0 <= sy < 8:
            row = m[sy] << dx if dx >= 0 else m[sy] >> -dx
            out[y] = row & 0xFF
    return bytes(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ewram", default=EWRAM_DUMP)
    parser.add_argument("--lo", type=lambda s: int(s, 0), default=GLYPH_CACHE_LO)
    parser.add_argument("--hi", type=lambda s: int(s, 0), default=GLYPH_CACHE_HI)
    args = parser.parse_args()
    ewram = Path(args.ewram).read_bytes()

    by_color: dict[int, list[bytes]] = {2: [], 3: []}
    layer_pairs = []
    for off in range(args.lo, args.hi, 32):
        t = ewram[off:off + 32]
        m2 = color_mask(t, 2)
        m3 = color_mask(t, 3)
        if any(m2):
            by_color[2].append(m2)
        if any(m3):
            by_color[3].append(m3)
        if any(m2) and any(m3):
            layer_pairs.append((m2, m3))

    for c in (2, 3):
        print(f"color={c}: {len(by_color[c])} non-blank layer masks "
              f"({len(set(by_color[c]))} unique)")

    # Verify shadow-shift hypothesis (should fail = jamo decomposition confirmed)
    print(f"\nShadow-shift test on {len(layer_pairs)} two-color tiles:")
    shifts = Counter()
    for m2, m3 in layer_pairs:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if shift_mask(m3, dx, dy) == m2:
                    shifts[(dx, dy)] += 1
    for (dx, dy), c in sorted(shifts.items(), key=lambda kv: -kv[1]):
        print(f"  m2 == shifted(m3, {dx:+d}, {dy:+d}): {c}")

    # Containment test: is m2 ⊆ m3 or vice versa?
    c2_in_c3 = sum(1 for m2, m3 in layer_pairs if all((a | b) == b for a, b in zip(m2, m3)))
    c3_in_c2 = sum(1 for m2, m3 in layer_pairs if all((a | b) == b for a, b in zip(m3, m2)))
    print(f"\nm2 ⊆ m3: {c2_in_c3}/{len(layer_pairs)}")
    print(f"m3 ⊆ m2: {c3_in_c2}/{len(layer_pairs)}")
    print("(both should be near 0 — confirming jamo decomposition rather than shadow)")


if __name__ == "__main__":
    main()
