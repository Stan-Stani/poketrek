#!/usr/bin/env python3
"""For each top-N unknown codepoint, render the ROM glyph at 8x next to
PIL renders of its candidate syllables (also at 8x), in candidate order.
Each unknown gets one row. Outputs a wide PNG plus a structured JSON
catalog with cp, candidate list, and (for our records) the best PIL
OCR guess.
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
OUT = Path("/tmp/poketrek_trace/unknown_labels")

# Best calibrated PIL config from earlier sweep
PIL_FONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
PIL_SIZE = 12
OFFSETS = [(dx, dy) for dx in range(-2, 3) for dy in range(-2, 3)]


def storage_to_internal(cp: int) -> int:
    return (((cp >> 8) & 0xff) - 0x35) << 8 | (cp & 0xff)


def render_rom_glyph(rom: bytes, cp: int) -> Image.Image | None:
    icp = storage_to_internal(cp)
    off = (ATLAS1_BASE - GBA_BASE) + icp * 64
    if off + 64 > len(rom):
        return None
    return decode_glyph(rom[off:off + 64], 16, 16)


def render_pil(font, ch, dx, dy):
    canvas = Image.new("L", (16, 16), 0)
    d = ImageDraw.Draw(canvas)
    d.text((dx, dy), ch, fill=255, font=font)
    return canvas


def best_pil_render(font, ch, target_arr):
    """Try all offsets, return (best_pil_image, best_score)."""
    best_im = None
    best_s = -1
    for dx, dy in OFFSETS:
        im = render_pil(font, ch, dx, dy)
        a = (np.asarray(im) > 64).astype(np.uint8)
        if a.sum() == 0:
            continue
        b = target_arr
        inter = int(np.logical_and(a, b).sum())
        union = int(np.logical_or(a, b).sum())
        s = inter / union if union else 0
        if s > best_s:
            best_s = s
            best_im = im
    return best_im, best_s


def lis_anchors(raw_known):
    anchors = [(int(k, 16), v, ord(v)) for k, v in raw_known.items()]
    anchors.sort()
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


def find_brackets(cp, lis):
    prev = None
    next_ = None
    for a in lis:
        if a[0] < cp:
            prev = a
        elif a[0] > cp and next_ is None:
            next_ = a
            break
    return prev, next_


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=200)
    ap.add_argument("--max-cands", type=int, default=20,
                    help="max candidates rendered per unknown")
    args = ap.parse_args()

    rom = ROM_PATH.read_bytes()
    raw_known = json.load(open(KNOWN_MAP_PATH))
    lis = lis_anchors(raw_known)
    unknowns = json.load(open(UNKNOWNS_PATH))["unknowns"][:args.top]
    print(f"top {len(unknowns)} unknowns; LIS anchors: {len(lis)}")

    OUT.mkdir(parents=True, exist_ok=True)
    pil_font = ImageFont.truetype(PIL_FONT, PIL_SIZE)
    try:
        small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 11)
    except Exception:
        small = ImageFont.load_default()

    cell_w = 96   # 16x16 -> 80 + padding
    cell_h = 110
    rows_per_sheet = 18
    glyph_zoom = 5

    catalog = []
    rows_data = []

    for i, entry in enumerate(unknowns):
        cp_hex = entry["codepoint"][2:]
        cp = int(cp_hex, 16)
        cnt = entry["occurrences"]
        unk = render_rom_glyph(rom, cp)
        if unk is None:
            continue
        unk_arr = (np.asarray(unk) > 64).astype(np.uint8)
        prev_a, next_a = find_brackets(cp, lis)
        cands = []
        if prev_a and next_a:
            cands = [chr(u) for u in range(prev_a[2] + 1, next_a[2])]
        elif next_a:
            cands = [chr(u) for u in range(0xAC00, next_a[2])]
        elif prev_a:
            cands = [chr(u) for u in range(prev_a[2] + 1, 0xD7A4)]

        # Score candidates
        scored = []
        for ch in cands:
            _, s = best_pil_render(pil_font, ch, unk_arr)
            scored.append((s, ch))
        scored.sort(reverse=True)

        catalog.append({
            "cp_hex": cp_hex,
            "occurrences": cnt,
            "prev_anchor": (prev_a[0], prev_a[1]) if prev_a else None,
            "next_anchor": (next_a[0], next_a[1]) if next_a else None,
            "candidates_count": len(cands),
            "candidates_top10_by_pil": [
                {"char": c, "score": round(s, 3)} for s, c in scored[:10]],
            "first_pil_pick": scored[0][1] if scored else None,
        })
        rows_data.append((cp_hex, cnt, prev_a, next_a, unk, scored, cands))

    # Render sheets, one row per unknown
    for sheet_idx, batch_start in enumerate(range(0, len(rows_data), rows_per_sheet)):
        batch = rows_data[batch_start:batch_start + rows_per_sheet]
        cells_per_row = 2 + min(args.max_cands, max(len(r[5]) for r in batch))
        sheet_w = cells_per_row * cell_w + 100
        sheet_h = len(batch) * cell_h + 30
        sheet = Image.new("RGB", (sheet_w, sheet_h), (32, 32, 32))
        draw = ImageDraw.Draw(sheet)
        draw.text((8, 8),
                  f"sheet {sheet_idx + 1} | top-{args.top} unknowns | "
                  f"col 1: ROM glyph + cp/count, "
                  f"col 2: prev anchor, "
                  f"cols 3+: candidates ranked by PIL OCR score",
                  fill=(220, 220, 220), font=small)

        for ri, (cp_hex, cnt, prev_a, next_a, unk, scored, cands) in enumerate(batch):
            y = 30 + ri * cell_h
            # ROM glyph (col 0)
            sheet.paste(unk.resize((80, 80), Image.NEAREST).convert("RGB"),
                        (8, y))
            draw.text((8, y + 88),
                      f"0x{cp_hex} (×{cnt})",
                      fill=(255, 240, 180), font=small)
            # Prev anchor (col 1)
            if prev_a:
                pg = render_rom_glyph(rom, prev_a[0])
                if pg:
                    sheet.paste(pg.resize((80, 80), Image.NEAREST).convert("RGB"),
                                (8 + cell_w, y))
                    draw.text((8 + cell_w, y + 88),
                              f"{prev_a[1]} 0x{prev_a[0]:04X}",
                              fill=(160, 220, 160), font=small)
            # Candidates ranked by PIL score (cols 2..)
            for ci, (s, ch) in enumerate(scored[:args.max_cands]):
                cx = 8 + (2 + ci) * cell_w
                # PIL render of candidate at the matching offset
                _, _ = best_pil_render(pil_font, ch, np.asarray(unk) > 64)
                # Just render at offset (0,0) for visibility
                pim = render_pil(pil_font, ch, 0, 0)
                sheet.paste(pim.resize((80, 80), Image.NEAREST).convert("RGB"),
                            (cx, y))
                draw.text((cx, y + 88), f"{ch}  {s:.2f}",
                          fill=(220, 220, 220), font=small)

        path = OUT / f"sheet_{sheet_idx:02d}.png"
        sheet.save(path)
        print(f"  wrote {path} ({sheet_w}x{sheet_h})")

    (OUT / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2))
    print(f"\ncatalog: {OUT}/catalog.json ({len(catalog)} entries)")


if __name__ == "__main__":
    main()
