#!/usr/bin/env python3
"""Take Korean text rendered live from EWRAM and search the ROM for the
encoded byte sequence. Distinguishes "corpus extractor missed a region"
from "text is runtime-synthesized."

Usage:
  python3 tools/moneo/find_text_in_rom.py "쿤는「은」좋미마을 하고있다!……좋아!나가볼까?"
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROM = ROOT / "Pocket Monsters - LeafGreen (Korean).gba"
GLYPH_MAP = ROOT / "tools/moneo/glyph-map.json"


def build_reverse(glyph_map: dict[str, str]) -> dict[str, list[bytes]]:
    """char -> list of possible (page, idx) byte encodings.
    F0,X -> single byte X. F1..F6,X -> two bytes (0xF0+page, X).
    Multiple keys can map to the same char; we keep all."""
    rev: dict[str, list[bytes]] = {}
    for k, ch in glyph_map.items():
        if not ch or "," not in k:
            continue
        page_str, idx_str = k.split(",", 1)
        page = int(page_str[1:])  # "F3" -> 3
        idx = int(idx_str)
        if page == 0:
            seq = bytes([idx])
        else:
            seq = bytes([0xF0 + page, idx])
        rev.setdefault(ch, []).append(seq)
    return rev


def encode_simple(text: str, rev: dict[str, list[bytes]]) -> tuple[bytes, list[str]]:
    """Encode using the FIRST encoding for each char. Returns (bytes, missing_chars)."""
    out = bytearray()
    missing: list[str] = []
    for ch in text:
        if ch in rev:
            out += rev[ch][0]
        else:
            missing.append(ch)
            out += b"\x00"  # placeholder, will not match
    return bytes(out), missing


def slide_search(rom: bytes, encoded: bytes, min_run: int = 4) -> list[tuple[int, int]]:
    """Find longest contiguous matching runs of `encoded` in `rom`.
    Returns list of (rom_offset, length_in_bytes) for runs >= min_run bytes."""
    hits = []
    n = len(encoded)
    if n < min_run:
        return hits
    # Try every starting position in the encoded text
    for start in range(n - min_run + 1):
        # Find longest run starting at `start` that appears in ROM
        for run_len in range(min(64, n - start), min_run - 1, -1):
            needle = encoded[start:start + run_len]
            off = rom.find(needle)
            if off >= 0:
                hits.append((off, run_len, start, needle))
                break
    return hits


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: find_text_in_rom.py <korean text>", file=sys.stderr)
        return 2
    text = sys.argv[1]
    glyph_map = json.loads(GLYPH_MAP.read_text())["map"]
    rev = build_reverse(glyph_map)

    encoded, missing = encode_simple(text, rev)
    print(f"text: {text!r}  ({len(text)} chars)")
    if missing:
        print(f"  missing chars (no glyph): {missing}")
    print(f"  encoded: {encoded.hex()}  ({len(encoded)} bytes)")

    rom = ROM.read_bytes()
    print(f"\nROM: {len(rom):,} bytes")

    # Whole-string exact match
    full = rom.find(encoded)
    if full >= 0:
        print(f"\n*** FULL MATCH at ROM offset 0x{full:X} ***")
        return 0

    # Try each char individually so we can see which char(s) cause the break
    print("\nLongest runs found at each starting char:")
    n = len(text)
    best = []
    for start in range(n):
        # encode from `start` and find longest prefix that exists in ROM
        prefix_bytes = bytearray()
        max_len = 0
        max_off = -1
        for end in range(start + 1, n + 1):
            ch = text[end - 1]
            if ch not in rev:
                break
            prefix_bytes += rev[ch][0]
            off = rom.find(bytes(prefix_bytes))
            if off < 0:
                break
            max_len = end - start
            max_off = off
        if max_len >= 3:
            best.append((max_len, start, max_off, text[start:start + max_len]))
    best.sort(reverse=True)
    for length, start, off, snippet in best[:10]:
        print(f"  {length:3d} chars from text[{start}] @ ROM 0x{off:X}: {snippet!r}")

    # Also report: how many *occurrences* does the longest run have?
    if best:
        length, start, off, snippet = best[0]
        sub = bytearray()
        for ch in snippet:
            sub += rev[ch][0]
        sub_b = bytes(sub)
        cnt = 0
        idx = 0
        offsets = []
        while True:
            f = rom.find(sub_b, idx)
            if f < 0:
                break
            offsets.append(f)
            cnt += 1
            idx = f + 1
            if cnt > 200:
                break
        print(f"\nLongest run {snippet!r} ({length} chars, {len(sub_b)} bytes) appears {cnt}x in ROM")
        if cnt <= 20:
            for o in offsets:
                print(f"  0x{o:X}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
