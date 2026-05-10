#!/usr/bin/env python3
"""Verify which atlas + indexing function maps each BE16 codepoint
(0x3700..0x40FF) to its glyph slot. We have 539 known cp -> syllable
mappings; render each cp from each atlas under several indexing
hypotheses and print the layout that produces visually consistent
hangul (e.g., for cp=0x3701 we should see "가").
"""
from __future__ import annotations
from pathlib import Path
import sys, json
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_jamo_atlas import decode_glyph

ROM = Path(__file__).resolve().parent / "leafgreen_J-K_2024.gba"
GBA_BASE = 0x08000000
CODEPOINT_MAP = Path(__file__).resolve().parent / "codepoint_map.json"

ATLASES = [
    ("atlas0", 0x08edf800, 32, 16, 8),
    ("atlas1", 0x08f18800, 64, 16, 16),
    ("atlas2", 0x08f51800, 64, 16, 16),
]

# Known anchors we'll render for visual verification.
ANCHORS = ["3701", "3702", "3703", "3713", "3753", "3801", "39EE", "3DFE"]


def render_at(rom: bytes, font_base: int, cp_index: int, src_per_glyph: int,
              w: int, h: int):
    off = (font_base - GBA_BASE) + cp_index * 64
    if off + src_per_glyph > len(rom):
        return None
    src = rom[off:off + src_per_glyph]
    return decode_glyph(src, w, h)


def main():
    rom = ROM.read_bytes()
    cm = json.load(open(CODEPOINT_MAP))
    out = Path("/tmp/poketrek_trace/atlas_render/verify")
    out.mkdir(parents=True, exist_ok=True)

    # Hypothesis A: cp_index = cp_value (no offset)
    # Hypothesis B: cp_index = cp_value - 0x3700
    # Hypothesis C: cp_index = cp_value - 0x3701 (so 가 -> idx 0)
    for hyp_label, transform in [
        ("raw", lambda cp: cp),
        ("minus_3700", lambda cp: cp - 0x3700),
        ("minus_3701", lambda cp: cp - 0x3701),
    ]:
        sheet_w = len(ATLASES) * (16 + 4)
        sheet_h = len(ANCHORS) * (16 + 4)
        sheet = Image.new("L", (sheet_w, sheet_h), 32)
        for row, cp_hex in enumerate(ANCHORS):
            cp = int(cp_hex, 16)
            idx = transform(cp)
            for col, (label, base, src_per, w, h) in enumerate(ATLASES):
                glyph = render_at(rom, base, idx, src_per, w, h)
                if glyph:
                    sheet.paste(glyph,
                                (col * (16 + 4), row * (16 + 4)))
        path = out / f"verify_{hyp_label}.png"
        sheet.resize((sheet.width * 8, sheet.height * 8), Image.NEAREST).save(path)
        print(f"hypothesis '{hyp_label}': {path}")
    print()
    print("anchors (top -> bottom):")
    for cp_hex in ANCHORS:
        print(f"  cp 0x{cp_hex} -> {cm.get(cp_hex, '?')}")


if __name__ == "__main__":
    main()
