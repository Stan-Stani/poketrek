#!/usr/bin/env python3
"""Compute (page, idx) -> VRAM 4bpp fingerprint using the LIVE blit table
extracted from IWRAM (.moneo-artifacts/dumps/iwram.bin).

Strategy:
  - table1 (256 bytes, ROM @ 0x081CDF1C): ROM byte -> pattern index (0..80)
  - table2 (256 halfwords, IWRAM @ 0x03000A40): pattern index -> VRAM halfword
  - For each (page, idx), iterate over the 4 sub-tiles (TL, TR, BL, BR),
    convert each 16-byte ROM 2bpp tile to 32-byte VRAM 4bpp tile, concat,
    then SHA-256 (truncated to 16 hex chars).

Tries multiple sub-tile permutations and ROM byte-pair orderings. Reports the
first ordering that matches the most entries in ko_charmap.json.
"""
from __future__ import annotations
import hashlib
import json
import struct
from itertools import permutations, product
from pathlib import Path

ROM = bytes(Path("Pocket Monsters - LeafGreen (Korean).gba").read_bytes())
IWRAM = bytes(Path(".moneo-artifacts/dumps/iwram.bin").read_bytes())
FONT_BASE = 0x780000

table1 = ROM[0x1CDF1C : 0x1CDF1C + 256]
table2 = struct.unpack_from("<256H", IWRAM, 0x0A40)


def blit_byte(rb: int) -> int:
    return table2[table1[rb]]


def blit_tile_v(rom_off: int, hi_first: bool) -> bytes:
    """Convert 16 ROM bytes (8 halfwords) -> 32 VRAM bytes (16 halfwords).

    For each ROM halfword, emit two VRAM halfwords. hi_first controls whether
    the high byte of the ROM halfword is processed first or second.
    """
    out = bytearray(32)
    for hw in range(8):
        b0 = ROM[rom_off + hw * 2]
        b1 = ROM[rom_off + hw * 2 + 1]
        first, second = (b1, b0) if hi_first else (b0, b1)
        v0 = blit_byte(first)
        v1 = blit_byte(second)
        out[hw * 4 + 0] = v0 & 0xFF
        out[hw * 4 + 1] = (v0 >> 8) & 0xFF
        out[hw * 4 + 2] = v1 & 0xFF
        out[hw * 4 + 3] = (v1 >> 8) & 0xFF
    return bytes(out)


def glyph_offsets(rom_page: int, idx: int):
    base = FONT_BASE + rom_page * 0x2000 + idx * 32
    # Standard sub-tile layout per disasm_engine.md:
    # TL @ +0, TR @ +16, BL @ +256, BR @ +272
    return base + 0, base + 16, base + 256, base + 272


def fingerprint(rom_page: int, idx: int, perm: tuple, hi_first: bool) -> str:
    offs = glyph_offsets(rom_page, idx)
    parts = [blit_tile_v(offs[i], hi_first) for i in perm]
    h = hashlib.sha256(b"".join(parts)).hexdigest()[:16]
    return h


def main() -> None:
    ko = json.loads(Path("app/src/main/assets/moneo/ko_charmap.json").read_text())
    fp_to_char = {fp: ch for fp, ch in ko.items()}
    print(f"ko_charmap fingerprints: {len(fp_to_char)}")

    # Build full token universe from the rom-text-ko-raw rip — but that file
    # may itself be wrong. Instead: every (page, idx) in pages 1..6, idx 0..255.
    candidates = [(p, i) for p in range(1, 7) for i in range(256)]
    print(f"candidate (page, idx) cells: {len(candidates)}")

    best = None
    for perm in permutations(range(4)):
        for hi_first in (False, True):
            fps = {}
            for (p, i) in candidates:
                fp = fingerprint(p, i, perm, hi_first)
                fps[(p, i)] = fp
            matched = sum(1 for fp in fps.values() if fp in fp_to_char)
            if best is None or matched > best[0]:
                best = (matched, perm, hi_first, fps)
                print(f"  perm={perm} hi_first={hi_first} -> matches={matched}")
    matched, perm, hi_first, fps = best
    print(f"\nBest: perm={perm} hi_first={hi_first} matches={matched}/{len(fp_to_char)}")

    # Show matches
    pi_to_char = {pi: fp_to_char[fp] for pi, fp in fps.items() if fp in fp_to_char}
    print(f"Resolved (page, idx) -> char: {len(pi_to_char)}")
    for (p, i), ch in sorted(pi_to_char.items())[:30]:
        print(f"  P{p},{i:3d} -> {ch!r}  fp={fps[(p, i)]}")

    Path(".moneo-artifacts/blit-fp-map.json").write_text(
        json.dumps(
            {
                "perm": list(perm),
                "hi_first": hi_first,
                "matched": matched,
                "fp_by_pi": {f"F{p},{i}": fp for (p, i), fp in fps.items()},
                "char_by_pi": {f"F{p},{i}": ch for (p, i), ch in pi_to_char.items()},
            },
            ensure_ascii=False,
            indent=1,
        )
    )
    print("\nWrote .moneo-artifacts/blit-fp-map.json")


if __name__ == "__main__":
    main()
