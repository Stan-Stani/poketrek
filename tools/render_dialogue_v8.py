#!/usr/bin/env python3
"""Render dialogue v8: 2D layout.

Rule: each text line is 2 sub-rows of 8 px. A byte with low nibble 0-7 is
placed at the next X column, top sub-row. A byte with low nibble 8-F is placed
at the SAME X column as the previously emitted glyph (no advance), but in the
bottom sub-row, forming the jongseong of a closed syllable.

If a jongseong appears with no preceding top in the same line (record starts
with jongseong, etc.), it is placed alone in the bottom sub-row at the next X.
"""
import json, os
from PIL import Image, ImageDraw, ImageFont

ROM_PATH = "Pocket Monsters - LeafGreen (Korean).gba"
FONT_BASE = 0x780000
BRIGHTNESS = [0, 255, 180, 100]
RAW = ".moneo-artifacts/rom-text-ko-raw.json"
OUT = ".moneo-artifacts/dialogue-v8"

with open(ROM_PATH, "rb") as fh:
    ROM = fh.read()


def render_glyph(off):
    img = Image.new("L", (16, 8), 0)
    p = img.load()
    for dx, to in ((0, 0), (8, 16)):
        for row in range(8):
            for half in range(2):
                b = ROM[off + to + row * 2 + (1 - half)]
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


def is_jong(idx):
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


def layout(toks):
    """Returns lines, each a list of cells. Each cell is a column with optional
    top-glyph and/or bottom-glyph and/or ctl-label."""
    lines = [[]]
    last_was_top = False  # whether current line's last cell ended with a top
    for kind, payload in toks:
        if kind == "END":
            break
        if kind == "NL":
            lines.append([])
            last_was_top = False
        elif kind in ("CTL", "CTL0"):
            label = (
                f"{'F' if payload[0] == 0xFC else 'V'}{payload[1]:02X}"
                if kind == "CTL"
                else f"0:{payload:02X}"
            )
            lines[-1].append({"ctl": label})
            last_was_top = False
        elif kind == "G":
            page, idx = payload
            g = (page, idx)
            if is_jong(idx) and last_was_top:
                # Stack onto previous cell's bottom slot
                cell = lines[-1][-1]
                cell["bot"] = g
                last_was_top = False
            else:
                cell = {}
                if is_jong(idx):
                    cell["bot"] = g
                    last_was_top = False
                else:
                    cell["top"] = g
                    last_was_top = True
                lines[-1].append(cell)
    return lines


def make_record_img(rec, font_small):
    lines = layout(tokenize(bytes.fromhex(rec["hex"])))

    S = 2
    CW, CH = 16 * S, 16 * S
    PAD = 1
    MAX_COLS = 32
    PAGE_W = MAX_COLS * (CW + PAD) + 4

    # Wrap long lines
    wrapped = []
    for line in lines:
        if not line:
            wrapped.append([]); continue
        for k in range(0, len(line), MAX_COLS):
            wrapped.append(line[k:k + MAX_COLS])

    h = 14 + max(1, len(wrapped)) * (CH + 2)
    img = Image.new("RGB", (PAGE_W, h), (15, 15, 25))
    dr = ImageDraw.Draw(img)
    dr.text((2, 1), f"@{rec['offset']:06X}", fill=(160, 180, 210), font=font_small)

    for ri, row in enumerate(wrapped):
        y = 14 + ri * (CH + 2)
        for ci, cell in enumerate(row):
            x = 2 + ci * (CW + PAD)
            if "ctl" in cell:
                dr.rectangle([x, y, x + CW, y + CH], fill=(70, 30, 30))
                dr.text((x + 1, y + 4), cell["ctl"][:6], fill=(255, 200, 200), font=font_small)
            else:
                dr.rectangle([x, y, x + CW, y + CH], fill=(20, 20, 30))
                if "top" in cell:
                    img.paste(
                        glyph(*cell["top"]).convert("RGB").resize((CW, 8 * S), Image.NEAREST),
                        (x, y),
                    )
                if "bot" in cell:
                    img.paste(
                        glyph(*cell["bot"]).convert("RGB").resize((CW, 8 * S), Image.NEAREST),
                        (x, y + 8 * S),
                    )
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
