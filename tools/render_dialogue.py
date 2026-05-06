#!/usr/bin/env python3
"""Render all 9999 dialogue records from the Korean LeafGreen ROM as PNG strips.

Font format (verified visually):
- 16x8 pixel glyphs at stride 32 bytes, 512 glyphs per ROM page.
- 6 ROM pages of 0x4000 bytes starting at 0x780000 -> 12 logical pages of 256 glyphs each.
- 2bpp packed: byte+1 = LEFT 4 px, byte+0 = RIGHT 4 px; HIGH 2 bits = leftmost pixel.

Token encoding (in raw text records):
- 0x00..0xEF                 -> page-0 glyph index
- 0xF1..0xF9 + idx           -> logical pages 1..9 glyph index
- 0xF0 + param               -> control / extended (TBD)
- 0xFC + param, 0xFD + param -> format / variable substitution (1 param byte)
- 0xFA, 0xFB, 0xFE           -> newline-ish
- 0xFF                       -> terminator
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

ROM_PATH = "Pocket Monsters - LeafGreen (Korean).gba"
FONT_BASE = 0x780000
BRIGHTNESS = [0, 255, 180, 100]
RAW_TEXT_JSON = ".moneo-artifacts/rom-text-ko-raw.json"
OUT_DIR = ".moneo-artifacts/dialogue-v5"

with open(ROM_PATH, "rb") as fh:
    ROM = fh.read()


def render_glyph(rom_off):
    img = Image.new("L", (16, 8), 0)
    pixels = img.load()
    for dx, to in ((0, 0), (8, 16)):
        for row in range(8):
            for half in range(2):
                b = ROM[rom_off + to + row * 2 + (1 - half)]
                for px in range(4):
                    v = (b >> ((3 - px) * 2)) & 0x3
                    if v:
                        pixels[dx + half * 4 + px, row] = BRIGHTNESS[v]
    return img


_GLYPH_CACHE = {}
def glyph(page, idx):
    k = (page, idx)
    g = _GLYPH_CACHE.get(k)
    if g is None:
        g = render_glyph(FONT_BASE + page * 0x2000 + idx * 32)
        _GLYPH_CACHE[k] = g
    return g


def tokenize(raw):
    out, i, n = [], 0, len(raw)
    while i < n:
        b = raw[i]
        if b == 0xFF:
            out.append(("END", None)); i += 1
        elif b in (0xFA, 0xFB, 0xFE):
            out.append(("NL", None)); i += 1
        elif b in (0xFC, 0xFD) and i + 1 < n:
            out.append(("CTL", (b, raw[i + 1]))); i += 2
        elif 0xF1 <= b <= 0xF9 and i + 1 < n:
            out.append(("G", (b - 0xF0, raw[i + 1]))); i += 2
        elif b == 0xF0 and i + 1 < n:
            out.append(("CTL0", raw[i + 1])); i += 2
        else:
            out.append(("G", (0, b))); i += 1
    return out


def main():
    with open(RAW_TEXT_JSON) as fh:
        d = json.load(fh)
    records = d["records"]

    S = 2
    GW, GH = 16 * S, 8 * S
    MAX_COLS = 48
    PAD = 1
    RECORDS_PER_PAGE = 40
    PAGE_W = MAX_COLS * (GW + PAD) + 4

    os.makedirs(OUT_DIR, exist_ok=True)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 8)
    except Exception:
        font = ImageFont.load_default()

    def make_record_img(rec):
        toks = tokenize(bytes.fromhex(rec["hex"]))
        rows = [[]]
        for kind, p in toks:
            if kind == "END":
                break
            if kind == "NL":
                rows.append([])
            elif len(rows[-1]) >= MAX_COLS:
                rows.append([(kind, p)])
            else:
                rows[-1].append((kind, p))
        h = 12 + len(rows) * (GH + 1)
        img = Image.new("RGB", (PAGE_W, h), (15, 15, 25))
        dr = ImageDraw.Draw(img)
        dr.text((2, 1), f"@{rec['offset']:06X}", fill=(160, 180, 210), font=font)
        for ri, row in enumerate(rows):
            y = 12 + ri * (GH + 1)
            for ci, (kind, p) in enumerate(row):
                x = 2 + ci * (GW + PAD)
                if kind == "G":
                    img.paste(
                        glyph(*p).convert("RGB").resize((GW, GH), Image.NEAREST),
                        (x, y),
                    )
                elif kind == "CTL":
                    dr.rectangle([x, y, x + GW, y + GH], fill=(70, 30, 30))
                    label = f"{'F' if p[0] == 0xFC else 'V'}{p[1]:02X}"
                    dr.text((x + 1, y), label, fill=(255, 200, 200), font=font)
                else:
                    dr.rectangle([x, y, x + GW, y + GH], fill=(40, 40, 60))
        return img

    total_pages = (len(records) + RECORDS_PER_PAGE - 1) // RECORDS_PER_PAGE
    for pi in range(total_pages):
        chunk = records[pi * RECORDS_PER_PAGE:(pi + 1) * RECORDS_PER_PAGE]
        rendered = [make_record_img(r) for r in chunk]
        H = sum(r.size[1] for r in rendered) + len(rendered) * 2 + 8
        page = Image.new("RGB", (PAGE_W, H), (8, 8, 15))
        y = 4
        for img in rendered:
            page.paste(img, (0, y))
            y += img.size[1] + 2
        page.save(f"{OUT_DIR}/page{pi:03d}.png", optimize=False)
        if pi % 25 == 0:
            print(f"{pi}/{total_pages}", flush=True)
    print(f"wrote {total_pages} pages to {OUT_DIR}")


if __name__ == "__main__":
    main()
