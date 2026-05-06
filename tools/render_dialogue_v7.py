#!/usr/bin/env python3
"""Render dialogue v7: pair every two consecutive glyph tokens into 16×16 cells.

Hypothesis: text is a stream of 16×8 half-glyphs. Each syllable = 2 consecutive
glyph tokens (top, then bottom). Control codes (CTL/CTL0/NL/END) split the
stream and are rendered between syllables; an odd straggler glyph is shown
alone in its top slot.
"""
import json, os
from PIL import Image, ImageDraw, ImageFont

ROM_PATH = "Pocket Monsters - LeafGreen (Korean).gba"
FONT_BASE = 0x780000
BRIGHTNESS = [0, 255, 180, 100]
RAW = ".moneo-artifacts/rom-text-ko-raw.json"
OUT = ".moneo-artifacts/dialogue-v7"

with open(ROM_PATH, "rb") as fh:
    ROM = fh.read()


def render_glyph(rom_off):
    img = Image.new("L", (16, 8), 0)
    p = img.load()
    for dx, to in ((0, 0), (8, 16)):
        for row in range(8):
            for half in range(2):
                b = ROM[rom_off + to + row * 2 + (1 - half)]
                for px in range(4):
                    v = (b >> ((3 - px) * 2)) & 0x3
                    if v:
                        p[dx + half * 4 + px, row] = BRIGHTNESS[v]
    return img


_GC = {}
def glyph(page, idx):
    k = (page, idx)
    if k not in _GC:
        _GC[k] = render_glyph(FONT_BASE + page * 0x2000 + idx * 32)
    return _GC[k]


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


def compose(toks):
    cells = []
    pending_top = None
    for kind, payload in toks:
        if kind == "END":
            break
        if kind == "G":
            if pending_top is None:
                pending_top = payload
            else:
                cells.append(("syl", pending_top, payload))
                pending_top = None
        else:
            # Flush any pending top as standalone
            if pending_top is not None:
                cells.append(("syl", pending_top, None))
                pending_top = None
            if kind == "NL":
                cells.append(("nl",))
            elif kind == "CTL":
                b, p = payload
                cells.append(("ctl", f"{'F' if b == 0xFC else 'V'}{p:02X}"))
            elif kind == "CTL0":
                cells.append(("ctl", f"0:{payload:02X}"))
    if pending_top is not None:
        cells.append(("syl", pending_top, None))
    return cells


def make_record_img(rec, font_small):
    cells = compose(tokenize(bytes.fromhex(rec["hex"])))

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
                    img.paste(glyph(*top).convert("RGB").resize((CW, 8 * S), Image.NEAREST), (x, y))
                if bot is not None:
                    img.paste(glyph(*bot).convert("RGB").resize((CW, 8 * S), Image.NEAREST), (x, y + 8 * S))
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
        font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 8)
    except Exception:
        font = ImageFont.load_default()
    RPP = 30
    total = (len(records) + RPP - 1) // RPP
    for pi in range(total):
        chunk = records[pi * RPP:(pi + 1) * RPP]
        rendered = [make_record_img(r, font) for r in chunk]
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
    print(f"wrote {total} pages")


if __name__ == "__main__":
    main()
