#!/usr/bin/env python3
"""Render ONE specific unknown codepoint at high zoom, with all its
constrained candidate syllables rendered alongside (PIL at large size).

Usage: render_one_unknown.py 0x3D7C
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_jamo_atlas import decode_glyph

ROM = Path(__file__).resolve().parent / "leafgreen_J-K_2024.gba"
GBA_BASE = 0x08000000
ATLAS1_BASE = 0x08f18800
KNOWN_MAP = Path(__file__).resolve().parent / "codepoint_map.json"
OUT_DIR = Path("/tmp/poketrek_trace/single_unknown")


def storage_to_internal(cp: int) -> int:
    return (((cp >> 8) & 0xff) - 0x35) << 8 | (cp & 0xff)


def render_rom_glyph(rom: bytes, cp: int):
    icp = storage_to_internal(cp)
    off = (ATLAS1_BASE - GBA_BASE) + icp * 64
    if off + 64 > len(rom):
        return None
    return decode_glyph(rom[off:off + 64], 16, 16)


def lis_anchors(raw_known):
    anchors = sorted([(int(k, 16), v, ord(v)) for k, v in raw_known.items()])
    n = len(anchors)
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
    ap.add_argument("cp", help="hex storage codepoint, e.g. 0x3D7C")
    ap.add_argument("--zoom", type=int, default=16,
                    help="zoom factor for ROM glyph (default 16x)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cp = int(args.cp.lower().lstrip("0x"), 16)
    rom = ROM.read_bytes()
    raw = json.load(open(KNOWN_MAP))
    lis = lis_anchors(raw)

    rom_glyph = render_rom_glyph(rom, cp)
    if rom_glyph is None:
        print("cp out of ROM"); sys.exit(1)

    # Find brackets
    prev_a, next_a = None, None
    for a in lis:
        if a[0] < cp:
            prev_a = a
        elif a[0] > cp and next_a is None:
            next_a = a; break
    cands = []
    if prev_a and next_a:
        cands = [chr(u) for u in range(prev_a[2] + 1, next_a[2])]
    elif next_a:
        cands = [chr(u) for u in range(0xAC00, next_a[2])]
    elif prev_a:
        cands = [chr(u) for u in range(prev_a[2] + 1, 0xD7A4)]

    print(f"cp 0x{cp:04X}")
    print(f"  prev anchor: {prev_a}")
    print(f"  next anchor: {next_a}")
    print(f"  {len(cands)} candidates: "
          f"{''.join(cands[:50])}{'...' if len(cands) > 50 else ''}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else OUT_DIR / f"cp_{cp:04X}.png"

    # Layout: ROM glyph on top (zoomed), all candidates below at same zoom
    cell = 16 * args.zoom  # e.g., 256 px at 16x
    pad = 8
    cands_per_row = 8
    cand_rows = (len(cands) + cands_per_row - 1) // cands_per_row
    label_h = 28
    sheet_w = cands_per_row * (cell + pad) + pad
    sheet_h = (cell + label_h + pad) + cand_rows * (cell + label_h + pad) + 60
    sheet = Image.new("RGB", (sheet_w, sheet_h), (40, 40, 40))
    draw = ImageDraw.Draw(sheet)
    try:
        small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 14)
    except Exception:
        small = ImageFont.load_default()
    try:
        cand_font = ImageFont.truetype(
            "/System/Library/Fonts/AppleSDGothicNeo.ttc", args.zoom * 14)
    except Exception:
        cand_font = small

    # Header
    prev_label = f"{prev_a[1]} (0x{prev_a[0]:04X})" if prev_a else "—"
    next_label = f"{next_a[1]} (0x{next_a[0]:04X})" if next_a else "—"
    draw.text((pad, pad),
              f"cp 0x{cp:04X}   prev: {prev_label}   next: {next_label}   "
              f"{len(cands)} candidates",
              fill=(220, 220, 220), font=small)

    # ROM glyph (top, centred)
    rom_zoom = rom_glyph.resize((cell, cell), Image.NEAREST).convert("RGB")
    sheet.paste(rom_zoom, (pad, pad + 24))
    draw.text((pad, pad + 24 + cell + 4), "ROM glyph",
              fill=(255, 240, 180), font=small)

    # Candidates
    base_y = pad + 24 + cell + label_h + 24
    for i, ch in enumerate(cands):
        col = i % cands_per_row
        row = i // cands_per_row
        x = pad + col * (cell + pad)
        y = base_y + row * (cell + label_h + pad)
        # Render PIL candidate at the matching zoom (try a font size that
        # fills the cell well: ~zoom*14 produced good fill).
        canvas = Image.new("L", (cell, cell), 0)
        d2 = ImageDraw.Draw(canvas)
        # Centre the character
        bbox = cand_font.getbbox(ch)
        bx = (cell - (bbox[2] - bbox[0])) // 2 - bbox[0]
        by = (cell - (bbox[3] - bbox[1])) // 2 - bbox[1]
        d2.text((bx, by), ch, fill=255, font=cand_font)
        sheet.paste(canvas.convert("RGB"), (x, y))
        draw.text((x, y + cell + 4), f"{i}: {ch}  U+{ord(ch):04X}",
                  fill=(220, 220, 220), font=small)

    sheet.save(out_path)
    print(f"  wrote {out_path}")


if __name__ == "__main__":
    main()
