#!/usr/bin/env python3
"""Pairwise glyph-similarity scan: find unknown codepoints whose ROM
glyph is byte-identical OR near-identical (≤4 differing pixels of 256)
to a labeled codepoint's glyph.

When found, classify:
  - If unknown's occurrences are all in the dialog region
    (offset >= 0x700000): treat as ALT-ENCODING and propose
    cp -> same syllable.
  - If occurrences are all in graphics/binary tables
    (offset <  0x700000): treat as CONTROL_ALIAS.
  - If mixed: flag for manual review.

Outputs:
  /tmp/poketrek_trace/glyph_dup_labels.json    — proposed cp -> char
  /tmp/poketrek_trace/glyph_dup_controls.json  — proposed control aliases
  /tmp/poketrek_trace/glyph_dup_mixed.json     — needs review
"""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from render_jamo_atlas import decode_glyph

ROM_PATH = Path(__file__).resolve().parent / "leafgreen_J-K_2024.gba"
GBA_BASE = 0x08000000
ATLAS1_BASE = 0x08f18800
MAP_PATH = Path(__file__).resolve().parent / "codepoint_map.json"
UNK_PATH = Path(__file__).resolve().parents[1] / "codepoint_unknowns_2024.json"
CORPUS_PATH = Path(__file__).resolve().parents[1] / "corpus.ko.2024.json"
CONTROL_PATH = Path(__file__).resolve().parent / "control_codes.json"

DIALOG_THRESHOLD = 0x700000


def storage_to_internal(cp: int) -> int:
    return (((cp >> 8) & 0xff) - 0x35) << 8 | (cp & 0xff)


def raw_glyph_bytes(rom: bytes, cp: int) -> bytes | None:
    icp = storage_to_internal(cp)
    off = (ATLAS1_BASE - GBA_BASE) + icp * 64
    if off + 64 > len(rom):
        return None
    return rom[off:off + 64]


def decoded_pixels(rom: bytes, cp: int) -> bytes | None:
    gb = raw_glyph_bytes(rom, cp)
    if gb is None:
        return None
    img = decode_glyph(gb, 16, 16)
    return bytes(img.getdata()) if img else None


def pixel_distance(a: bytes, b: bytes) -> int:
    """Number of differing pixels between two 16x16 glyph bitmaps."""
    # Binarize each side to (on/off) then count XOR
    return sum(1 for x, y in zip(a, b) if (x > 64) != (y > 64))


def main():
    rom = ROM_PATH.read_bytes()
    m = json.load(open(MAP_PATH))
    unknowns = json.load(open(UNK_PATH))["unknowns"]
    corpus = json.load(open(CORPUS_PATH))
    controls = json.load(open(CONTROL_PATH))

    # Build list of (cp, syllable, pixels) from labeled cps
    DIST_THRESHOLD = 4  # max differing pixels for "near-match"
    labeled = []
    for cp_hex, ch in m.items():
        cp = int(cp_hex, 16)
        px = decoded_pixels(rom, cp)
        if px is None or sum(1 for p in px if p > 64) < 4:  # skip near-blanks
            continue
        labeled.append((cp_hex.upper(), ch, px))

    # Build cp -> occurrence-offset list
    cp_offsets: dict[str, list[int]] = {}
    for r in corpus["records"]:
        off = r["offset"]
        t = r["text"]
        # find any [HEXHEX] markers
        i = 0
        while True:
            i = t.find("[", i)
            if i < 0: break
            j = t.find("]", i)
            if j < 0 or j - i not in (5,):  # [XXXX]
                i = max(i, 0) + 1; continue
            cp_hex = t[i+1:j].upper()
            if all(c in "0123456789ABCDEF" for c in cp_hex):
                cp_offsets.setdefault(cp_hex, []).append(off)
            i = j + 1

    proposals: dict[str, str] = {}
    control_aliases: dict[str, dict] = {}
    mixed: dict[str, dict] = {}
    no_match: list[str] = []
    blanks: list[str] = []

    for u in unknowns:
        cp_hex = u["codepoint"][2:].upper()
        if cp_hex in controls:
            continue
        cp = int(cp_hex, 16)
        px = decoded_pixels(rom, cp)
        if px is None or sum(1 for p in px if p > 64) < 4:
            blanks.append(cp_hex); continue
        # Find nearest labeled glyph by pixel distance
        best = None
        best_d = DIST_THRESHOLD + 1
        for lcp, lch, lpx in labeled:
            d = pixel_distance(px, lpx)
            if d < best_d:
                best_d = d; best = (lcp, lch, d)
                if d == 0:
                    break
        if best is None:
            no_match.append(cp_hex); continue
        syllable = best[1]
        matches = [(best[0], best[1])]

        offs = cp_offsets.get(cp_hex, [])
        in_dialog = sum(1 for o in offs if o >= DIALOG_THRESHOLD)
        in_binary = sum(1 for o in offs if o <  DIALOG_THRESHOLD)
        if in_dialog and not in_binary:
            proposals[cp_hex] = syllable
        elif in_binary and not in_dialog:
            control_aliases[cp_hex] = {
                "role": "CONTROL_ALIAS",
                "aliased_cp": matches[0][0],
                "glyph_syllable": syllable,
                "hypothesis": f"Glyph byte-identical to labeled cp(s) "
                              f"rendering '{syllable}'. All {in_binary} "
                              f"occurrences in graphics/binary-table region "
                              f"(offset < 0x{DIALOG_THRESHOLD:X}).",
            }
        else:
            mixed[cp_hex] = {
                "glyph_syllable": syllable,
                "aliased_cps": [c for c, _ in matches],
                "occ_in_dialog": in_dialog,
                "occ_in_binary": in_binary,
            }

    Path("/tmp/poketrek_trace/glyph_dup_labels.json").write_text(
        json.dumps({k: proposals[k] for k in sorted(proposals)},
                   indent=2, ensure_ascii=False))
    Path("/tmp/poketrek_trace/glyph_dup_controls.json").write_text(
        json.dumps(control_aliases, indent=2, ensure_ascii=False))
    Path("/tmp/poketrek_trace/glyph_dup_mixed.json").write_text(
        json.dumps(mixed, indent=2, ensure_ascii=False))

    print(f"unknowns scanned: {len(unknowns)}")
    print(f"  already classified control: {sum(1 for u in unknowns if u['codepoint'][2:].upper() in controls)}")
    print(f"  blank glyph (skip):         {len(blanks)}")
    print(f"  no glyph match:             {len(no_match)}")
    print(f"  PROPOSED alt-encoding:      {len(proposals)}")
    print(f"  PROPOSED control alias:     {len(control_aliases)}")
    print(f"  mixed (manual review):      {len(mixed)}")
    print()
    print("Sample alt-encoding proposals:")
    for k, v in list(proposals.items())[:15]:
        print(f"  0x{k} -> {v}")


if __name__ == "__main__":
    main()
