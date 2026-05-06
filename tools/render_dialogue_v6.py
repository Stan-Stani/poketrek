#!/usr/bin/env python3
"""Render all 9999 dialogue records — composing top+bottom glyph pairs into
proper 16×16 Korean syllables.

Glyph format (verified):
- Each font cell is 16×8 px (stride 32 bytes), 256 cells per logical page,
  12 logical pages (`FONT_BASE + page*0x2000 + idx*32`).
- Within ANY page, indices with low nibble 0..7 are TOP halves (open syllables);
  indices with low nibble 8..F are BOTTOM halves (jongseong / 받침 overlays).
- A closed syllable in text = top byte then bottom byte rendered stacked into
  a 16×16 cell. An open syllable is a top byte alone (bottom row blank).

Token encoding:
- 0xF1..0xF9 + idx → glyph from logical pages 1..9 (high pages have more syllables).
- 0xFC/0xFD + 1 param → format/variable substitution.
- 0xFA/0xFB/0xFE → newline. 0xFF → terminator.
- 0xF0 + param → reserved (treated as control).
- All other bytes → page-0 glyph.
"""
import json, os
from PIL import Image, ImageDraw, ImageFont

ROM_PATH = "Pocket Monsters - LeafGreen (Korean).gba"
FONT_BASE = 0x780000
BRIGHTNESS = [0, 255, 180, 100]
RAW = ".moneo-artifacts/rom-text-ko-raw.json"
OUT = ".moneo-artifacts/dialogue-v6"

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


_GCACHE = {}
def glyph(page, idx):
    k = (page, idx)
    g = _GCACHE.get(k)
    if g is None:
        g = render_glyph(FONT_BASE + page * 0x2000 + idx * 32)
        _GCACHE[k] = g
    return g


def is_jongseong(idx):
    """Bottom-half / jongseong glyph — low nibble 8..F."""
    return (idx & 0x08) != 0


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


def compose_syllables(toks):
    """Walk tokens; combine consecutive [top, bottom] glyph pairs into 16×16
    syllable cells. A 'top' is a glyph token with even-bit-3 idx; a 'bottom'
    is one with idx & 8 set."""
    cells = []  # each: ('syl', top_img, bot_img|None) or ('ctl', label) or ('nl',)
    i = 0
    while i < len(toks):
        kind, payload = toks[i]
        if kind == "END":
            break
        if kind == "NL":
            cells.append(("nl",)); i += 1
        elif kind == "CTL":
            b, p = payload
            cells.append(("ctl", f"{'F' if b == 0xFC else 'V'}{p:02X}")); i += 1
        elif kind == "CTL0":
            cells.append(("ctl", f"0:{payload:02X}")); i += 1
        elif kind == "G":
            page, idx = payload
            top_img = glyph(page, idx)
            top_is_jong = is_jongseong(idx)
            # Look ahead: if the next token is a glyph that is a jongseong, pair it.
            bot_img = None
            if (
                not top_is_jong
                and i + 1 < len(toks)
                and toks[i + 1][0] == "G"
                and is_jongseong(toks[i + 1][1][1])
            ):
                bp, bi = toks[i + 1][1]
                bot_img = glyph(bp, bi)
                i += 2
            else:
                # Standalone — could be open syllable (top) or stray jongseong.
                # If it's a stray jongseong, render it in the bottom slot for clarity.
                if top_is_jong:
                    cells.append(("syl", None, top_img))
                    i += 1
                    continue
                i += 1
            cells.append(("syl", top_img, bot_img))
        else:
            i += 1
    return cells


def make_record_img(rec, font_small):
    toks = tokenize(bytes.fromhex(rec["hex"]))
    cells = compose_syllables(toks)

    S = 2
    CW, CH = 16 * S, 16 * S
    PAD = 1
    MAX_COLS = 32
    PAGE_W = MAX_COLS * (CW + PAD) + 4

    rows = [[]]
    for c in cells:
        if c[0] == "nl":
            rows.append([])
        elif len(rows[-1]) >= MAX_COLS:
            rows.append([c])
        else:
            rows[-1].append(c)

    h = 14 + len(rows) * (CH + 2)
    img = Image.new("RGB", (PAGE_W, h), (15, 15, 25))
    dr = ImageDraw.Draw(img)
    dr.text((2, 1), f"@{rec['offset']:06X}", fill=(160, 180, 210), font=font_small)

    for ri, row in enumerate(rows):
        y = 14 + ri * (CH + 2)
        for ci, c in enumerate(row):
            x = 2 + ci * (CW + PAD)
            if c[0] == "syl":
                _, top, bot = c
                dr.rectangle([x, y, x + CW, y + CH], fill=(20, 20, 30))
                if top is not None:
                    img.paste(
                        top.convert("RGB").resize((CW, 8 * S), Image.NEAREST),
                        (x, y),
                    )
                if bot is not None:
                    img.paste(
                        bot.convert("RGB").resize((CW, 8 * S), Image.NEAREST),
                        (x, y + 8 * S),
                    )
            elif c[0] == "ctl":
                dr.rectangle([x, y, x + CW, y + CH], fill=(70, 30, 30))
                dr.text((x + 1, y + 4), c[1][:6], fill=(255, 200, 200), font=font_small)
    return img


def main():
    with open(RAW) as fh:
        d = json.load(fh)
    records = d["records"]

    os.makedirs(OUT, exist_ok=True)
    try:
        font_small = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 8)
    except Exception:
        font_small = ImageFont.load_default()

    RECS_PER_PAGE = 30
    total = (len(records) + RECS_PER_PAGE - 1) // RECS_PER_PAGE

    for pi in range(total):
        chunk = records[pi * RECS_PER_PAGE:(pi + 1) * RECS_PER_PAGE]
        rendered = [make_record_img(r, font_small) for r in chunk]
        W = max(r.size[0] for r in rendered)
        H = sum(r.size[1] for r in rendered) + len(rendered) * 2 + 8
        page = Image.new("RGB", (W, H), (8, 8, 15))
        y = 4
        for img in rendered:
            page.paste(img, (0, y))
            y += img.size[1] + 2
        page.save(f"{OUT}/page{pi:03d}.png", optimize=False)
        if pi % 25 == 0:
            print(f"{pi}/{total}", flush=True)
    print(f"wrote {total} pages to {OUT}")


if __name__ == "__main__":
    main()
