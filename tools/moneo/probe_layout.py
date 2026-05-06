#!/usr/bin/env python3
"""Probe ROM Korean font layout by matching against ko_charmap.json fingerprints.

Goal: discover the (page_byte, idx_byte) -> ROM_glyph_data mapping by searching
for ROM glyph slots whose 4bpp-VRAM-bytes hash to known fingerprints from
app/src/main/assets/moneo/ko_charmap.json.

The 46 fingerprints in ko_charmap are SHA-256[:8] of 128 bytes representing
4 contiguous 8x8 4bpp tiles in the order (TL, TR, BL, BR) — exactly how
VramTextReader.decode reads them.
"""
import hashlib
import json
import sys
from pathlib import Path

ROM_PATH = Path("Pocket Monsters - LeafGreen (Korean).gba")
KO_CHARMAP = Path("app/src/main/assets/moneo/ko_charmap.json")
FONT_BASE = 0x780000
PAGE_BYTES = 0x4000
NUM_PAGES = 6


def load_rom():
    return ROM_PATH.read_bytes()


def load_fingerprints():
    return json.loads(KO_CHARMAP.read_text(encoding="utf-8"))


# ---- 2bpp -> 4bpp tile transformation candidates ----------------------------

def decompress_2bpp_v1(src16):
    """v8 byte-swap layout: byte at +1 = left 4 px, byte at +0 = right 4 px,
    high 2 bits of each byte = leftmost pixel.
    Output is 32 bytes: 4 bytes per row of 8 px, 4bpp low-nibble-first."""
    out = bytearray(32)
    for row in range(8):
        b_left = src16[row * 2 + 1]
        b_right = src16[row * 2 + 0]
        # extract 8 pixel values
        px = [
            (b_left >> 6) & 3, (b_left >> 4) & 3, (b_left >> 2) & 3, (b_left >> 0) & 3,
            (b_right >> 6) & 3, (b_right >> 4) & 3, (b_right >> 2) & 3, (b_right >> 0) & 3,
        ]
        # 4bpp packing: low-nibble = even-x pixel
        for i in range(4):
            out[row * 4 + i] = (px[2 * i + 1] << 4) | px[2 * i]
    return bytes(out)


def decompress_2bpp_v2(src16):
    """LSB-first within byte (no byte swap)."""
    out = bytearray(32)
    for row in range(8):
        b0 = src16[row * 2 + 0]
        b1 = src16[row * 2 + 1]
        px = [
            (b0 >> 0) & 3, (b0 >> 2) & 3, (b0 >> 4) & 3, (b0 >> 6) & 3,
            (b1 >> 0) & 3, (b1 >> 2) & 3, (b1 >> 4) & 3, (b1 >> 6) & 3,
        ]
        for i in range(4):
            out[row * 4 + i] = (px[2 * i + 1] << 4) | px[2 * i]
    return bytes(out)


def decompress_2bpp_v3(src16):
    """v1 with high-nibble-first 4bpp packing."""
    out = bytearray(32)
    for row in range(8):
        b_left = src16[row * 2 + 1]
        b_right = src16[row * 2 + 0]
        px = [
            (b_left >> 6) & 3, (b_left >> 4) & 3, (b_left >> 2) & 3, (b_left >> 0) & 3,
            (b_right >> 6) & 3, (b_right >> 4) & 3, (b_right >> 2) & 3, (b_right >> 0) & 3,
        ]
        for i in range(4):
            out[row * 4 + i] = (px[2 * i] << 4) | px[2 * i + 1]
    return bytes(out)


def decompress_2bpp_v4(src16):
    """No swap, MSB-first within byte."""
    out = bytearray(32)
    for row in range(8):
        b0 = src16[row * 2 + 0]
        b1 = src16[row * 2 + 1]
        px = [
            (b0 >> 6) & 3, (b0 >> 4) & 3, (b0 >> 2) & 3, (b0 >> 0) & 3,
            (b1 >> 6) & 3, (b1 >> 4) & 3, (b1 >> 2) & 3, (b1 >> 0) & 3,
        ]
        for i in range(4):
            out[row * 4 + i] = (px[2 * i + 1] << 4) | px[2 * i]
    return bytes(out)


DECOMPRESSORS = {
    "v1_msb_swap_lo4": decompress_2bpp_v1,
    "v2_lsb_noswap_lo4": decompress_2bpp_v2,
    "v3_msb_swap_hi4": decompress_2bpp_v3,
    "v4_msb_noswap_lo4": decompress_2bpp_v4,
}


# ---- Glyph layout candidates ------------------------------------------------

def glyph_pokefirered(page_idx, glyph_id, rom):
    """16x16 glyph in pokefirered grid layout: 16 cols x 32 rows.
    Returns 4 sub-tiles (TL, TR, BL, BR) of 16 bytes each."""
    page_base = FONT_BASE + page_idx * PAGE_BYTES
    row = glyph_id // 16
    col = glyph_id % 16
    base = page_base + 0x200 * row + 0x20 * col
    return [
        bytes(rom[base + 0:base + 16]),       # TL
        bytes(rom[base + 16:base + 32]),      # TR
        bytes(rom[base + 256:base + 272]),    # BL
        bytes(rom[base + 272:base + 288]),    # BR
    ]


def glyph_linear_64(page_idx, glyph_id, rom):
    """64-byte glyph stored linearly: TL, TR, BL, BR contiguously."""
    page_base = FONT_BASE + page_idx * PAGE_BYTES
    base = page_base + glyph_id * 64
    if base + 64 > len(rom):
        return None
    return [bytes(rom[base + i*16:base + (i+1)*16]) for i in range(4)]


def glyph_linear_64_TLBL_TRBR(page_idx, glyph_id, rom):
    """64-byte glyph: TL, BL, TR, BR (column-major sub-tile order)."""
    page_base = FONT_BASE + page_idx * PAGE_BYTES
    base = page_base + glyph_id * 64
    if base + 64 > len(rom):
        return None
    parts = [bytes(rom[base + i*16:base + (i+1)*16]) for i in range(4)]
    # parts = [TL, BL, TR, BR] -> reorder to [TL, TR, BL, BR]
    return [parts[0], parts[2], parts[1], parts[3]]


GLYPH_LAYOUTS = {
    "pokefirered_16x16grid": glyph_pokefirered,
    "linear64_TLTRBLBR": glyph_linear_64,
    "linear64_TLBLTRBR": glyph_linear_64_TLBL_TRBR,
}


def fingerprint(subtiles, decompressor):
    if subtiles is None:
        return None
    raw = b"".join(decompressor(t) for t in subtiles)
    return hashlib.sha256(raw).hexdigest()[:16]


def main():
    rom = load_rom()
    fps = load_fingerprints()  # fp -> char
    print(f"Loaded ROM ({len(rom)} bytes), {len(fps)} known fingerprints")

    results = {}
    for layout_name, layout_fn in GLYPH_LAYOUTS.items():
        for dec_name, dec_fn in DECOMPRESSORS.items():
            matches = []
            for page in range(NUM_PAGES):
                # determine slot count for this layout
                if "pokefirered" in layout_name:
                    slots = 512
                else:
                    slots = 256
                for slot in range(slots):
                    parts = layout_fn(page, slot, rom)
                    if parts is None:
                        continue
                    if all(b == 0 for t in parts for b in t):
                        continue
                    fp = fingerprint(parts, dec_fn)
                    if fp in fps:
                        matches.append((page + 1, slot, fps[fp], fp))
            key = f"{layout_name} / {dec_name}"
            results[key] = matches
            print(f"  {key}: {len(matches)} matches")
            if matches:
                for m in matches[:5]:
                    print(f"     page F{m[0]} slot {m[1]} -> {m[2]} ({m[3]})")

    # Save best
    best_key = max(results, key=lambda k: len(results[k]))
    print(f"\nBest: {best_key} with {len(results[best_key])} matches out of {len(fps)}")
    out = {
        "best_key": best_key,
        "matches": [
            {"page": m[0], "slot": m[1], "char": m[2], "fp": m[3]}
            for m in results[best_key]
        ],
    }
    out_path = Path(".moneo-artifacts/probe-layout.json")
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {out_path}")


if __name__ == "__main__":
    main()
