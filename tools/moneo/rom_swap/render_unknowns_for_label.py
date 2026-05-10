#!/usr/bin/env python3
"""Render the top-N most-frequent unknown codepoints from the dialog
corpus as a labeled inspection sheet, with each row showing:
  prev_anchor_glyph | unknown_glyph (2x size) | next_anchor_glyph
with text annotations giving the cp, the bracketing anchors, the
constrained candidate range, and the count.

A human (or an AI vision model) can label these visually in minutes;
the labels go into manual_codepoint_labels.json which is merged into
codepoint_map.json by `apply_manual_codepoint_labels.py`.
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
UNKNOWNS_PATH = Path(__file__).resolve().parents[1] / "codepoint_unknowns_2024.json"
OUT_PATH = Path("/tmp/poketrek_trace/unknown_labels")


def storage_to_internal(cp: int) -> int:
    return (((cp >> 8) & 0xff) - 0x35) << 8 | (cp & 0xff)


def render_rom_glyph(rom: bytes, cp: int) -> Image.Image | None:
    icp = storage_to_internal(cp)
    off = (ATLAS1_BASE - GBA_BASE) + icp * 64
    if off + 64 > len(rom):
        return None
    return decode_glyph(rom[off:off + 64], 16, 16)


def find_brackets(cp: int, anchors: list[tuple[int, str, int]]):
    prev = None
    next_ = None
    for a in anchors:
        if a[0] < cp:
            prev = a
        elif a[0] > cp and next_ is None:
            next_ = a
            break
    return prev, next_


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=200)
    ap.add_argument("--cell", type=int, default=64)
    args = ap.parse_args()

    rom = ROM_PATH.read_bytes()
    raw_known: dict[str, str] = json.load(open(KNOWN_MAP_PATH))

    # Self-validate to LIS
    # (For brevity reuse the v3 logic: drop entries that break monotonicity
    # when sorted by cp.)
    anchors = [(int(k, 16), v, ord(v)) for k, v in raw_known.items()]
    anchors.sort()
    # LIS
    n = len(anchors)
    dp = [1] * n
    prev_idx = [-1] * n
    for i in range(n):
        for j in range(i):
            if anchors[j][2] < anchors[i][2] and dp[j] + 1 > dp[i]:
                dp[i] = dp[j] + 1
                prev_idx[i] = j
    end = max(range(n), key=lambda i: dp[i])
    lis = []
    while end != -1:
        lis.append(anchors[end])
        end = prev_idx[end]
    lis.reverse()

    unknowns = json.load(open(UNKNOWNS_PATH))["unknowns"]
    top = unknowns[:args.top]

    OUT_PATH.mkdir(parents=True, exist_ok=True)

    # Build a sheet: 5 cps per row, each cell ~360x100 px
    cell_w = 360
    cell_h = 100
    cols = 4
    rows = (len(top) + cols - 1) // cols
    sheet_w = cols * cell_w + 20
    sheet_h = rows * cell_h + 60
    sheet = Image.new("RGB", (sheet_w, sheet_h), (32, 32, 32))
    draw = ImageDraw.Draw(sheet)
    try:
        small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 11)
        big = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 28)
    except Exception:
        small = ImageFont.load_default()
        big = ImageFont.load_default()
    draw.text((8, 8), f"top {len(top)} unknown codepoints by occurrence "
                       f"(left col = prev anchor, middle = unknown ROM glyph "
                       f"@4x, right col = next anchor)",
              fill=(220, 220, 220), font=small)

    catalog = []
    for i, entry in enumerate(top):
        cp_hex = entry["codepoint"][2:]  # "0x3A37" -> "3A37"
        cp = int(cp_hex, 16)
        cnt = entry["occurrences"]
        unknown_glyph = render_rom_glyph(rom, cp)
        if unknown_glyph is None:
            continue
        prev_a, next_a = find_brackets(cp, lis)
        prev_g = render_rom_glyph(rom, prev_a[0]) if prev_a else None
        next_g = render_rom_glyph(rom, next_a[0]) if next_a else None
        # Candidate set = unicode range strictly between bracketing
        cands = []
        if prev_a and next_a:
            for u in range(prev_a[2] + 1, next_a[2]):
                cands.append(chr(u))
        elif next_a:
            for u in range(0xAC00, next_a[2]):
                cands.append(chr(u))
        elif prev_a:
            for u in range(prev_a[2] + 1, 0xD7A4):
                cands.append(chr(u))

        col = i % cols
        row = i // cols
        x = col * cell_w + 10
        y = row * cell_h + 40
        # cell border
        draw.rectangle([x, y, x + cell_w - 4, y + cell_h - 4],
                       outline=(80, 80, 80), width=1)
        # prev anchor (left)
        if prev_g:
            sheet.paste(prev_g.resize((48, 48), Image.NEAREST).convert("RGB"),
                        (x + 8, y + 8))
            draw.text((x + 8, y + 56),
                      f"prev 0x{prev_a[0]:04X}={prev_a[1]}",
                      fill=(160, 200, 160), font=small)
        # unknown (middle, larger)
        sheet.paste(unknown_glyph.resize((80, 80), Image.NEAREST).convert("RGB"),
                    (x + 64, y + 8))
        draw.text((x + 64, y + 90),
                  f"0x{cp_hex} (×{cnt})",
                  fill=(255, 240, 180), font=small)
        # next anchor (right)
        if next_g:
            sheet.paste(next_g.resize((48, 48), Image.NEAREST).convert("RGB"),
                        (x + 156, y + 8))
            draw.text((x + 156, y + 56),
                      f"next 0x{next_a[0]:04X}={next_a[1]}",
                      fill=(160, 200, 160), font=small)
        # candidate range (right side of cell)
        cand_str = "".join(cands[:60])
        if len(cands) > 60:
            cand_str += "..."
        # Wrap candidate string
        draw.text((x + 212, y + 4), f"{len(cands)} cands:",
                  fill=(180, 180, 180), font=small)
        # Render candidates with the smaller hangul font
        try:
            cand_font = ImageFont.truetype(
                "/System/Library/Fonts/AppleSDGothicNeo.ttc", 10)
        except Exception:
            cand_font = small
        # Wrap roughly every 12 chars
        for li, line_start in enumerate(range(0, len(cand_str), 12)):
            draw.text((x + 212, y + 18 + li * 12),
                      cand_str[line_start:line_start + 12],
                      fill=(220, 220, 220), font=cand_font)

        catalog.append({
            "cp_hex": cp_hex,
            "occurrences": cnt,
            "prev_anchor": (f"0x{prev_a[0]:04X}", prev_a[1]) if prev_a else None,
            "next_anchor": (f"0x{next_a[0]:04X}", next_a[1]) if next_a else None,
            "candidates": cands,
        })

    sheet.save(OUT_PATH / "top_unknowns_sheet.png")
    (OUT_PATH / "top_unknowns_catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2))
    print(f"sheet: {OUT_PATH}/top_unknowns_sheet.png ({sheet_w}x{sheet_h})")
    print(f"catalog: {OUT_PATH}/top_unknowns_catalog.json ({len(catalog)} entries)")


if __name__ == "__main__":
    main()
