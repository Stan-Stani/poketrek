#!/usr/bin/env python3
"""
Build glyph-table.json by OCR'ing all non-blank Korean ROM glyphs.

Uses the CORRECT 2bpp grid font format (byte+1=left, high bits=leftmost).
Output: .moneo-artifacts/glyph-table.json mapping "F<page>,<idx>" → unicode char
"""
import os
import sys
import json
import time

try:
    from PIL import Image
    import pytesseract
except ImportError:
    print("Requires: pip install Pillow pytesseract", file=sys.stderr)
    sys.exit(1)

ROM = "Pocket Monsters - LeafGreen (Korean).gba"
ART = ".moneo-artifacts"
FONT_BASE = 0x780000
PAGES = 6
PAGE_SIZE = 0x4000
GLYPHS_PER_PAGE = 512


def goff(gid):
    return 0x200 * (gid // 16) + 0x20 * (gid % 16)


def is_blank(rom, base, gid):
    o = base + goff(gid)
    return all(rom[o + t + i] == 0 for t in [0, 16, 256, 272] for i in range(16))


def render_glyph(rom, base, gid, scale=14):
    """Render glyph in CORRECT format: byte+1=left half, high bits=leftmost."""
    o = base + goff(gid)
    img = Image.new('L', (16, 16), 0)
    for dx, dy, toff in [(0, 0, 0), (8, 0, 16), (0, 8, 256), (8, 8, 272)]:
        for row in range(8):
            left = rom[o + toff + row * 2 + 1]
            right = rom[o + toff + row * 2 + 0]
            for px in range(4):
                vL = (left >> ((3 - px) * 2)) & 0x3
                vR = (right >> ((3 - px) * 2)) & 0x3
                if vL:
                    img.putpixel((dx + px, dy + row), 255)
                if vR:
                    img.putpixel((dx + 4 + px, dy + row), 255)
    big = img.resize((16 * scale, 16 * scale), Image.NEAREST)
    pad = scale * 4
    out = Image.new('L', (big.width + pad * 2, big.height + pad * 2), 255)
    for y in range(big.height):
        for x in range(big.width):
            if big.getpixel((x, y)) > 0:
                out.putpixel((x + pad, y + pad), 0)
    return out


def main():
    with open(ROM, 'rb') as f:
        rom = f.read()

    os.makedirs(ART, exist_ok=True)
    out_path = os.path.join(ART, 'glyph-table.json')

    # Resume support: skip already-processed entries
    table = {}
    if os.path.exists(out_path):
        try:
            with open(out_path, encoding='utf-8') as f:
                table = json.load(f)
            print(f"Resuming with {len(table)} existing entries", flush=True)
        except Exception:
            pass

    # Collect work
    work = []
    for page in range(PAGES):
        base = FONT_BASE + page * PAGE_SIZE
        for gid in range(GLYPHS_PER_PAGE):
            if is_blank(rom, base, gid):
                continue
            key = f'F{page+1},{gid}'
            if key in table:
                continue
            work.append((page + 1, gid, base))

    print(f"Total non-blank glyphs to OCR: {len(work)}", flush=True)

    cfg = '--psm 10 --oem 1'  # single character mode
    success = 0
    fail = 0
    start = time.time()
    last_save = start

    for i, (page_num, gid, base) in enumerate(work):
        img = render_glyph(rom, base, gid)
        try:
            txt = pytesseract.image_to_string(img, lang='kor', config=cfg).strip()
            # Keep first character if it's Hangul or common punctuation
            ch = ''
            for c in txt:
                if '\uAC00' <= c <= '\uD7A3' or '\u3130' <= c <= '\u318F':
                    ch = c
                    break
            if ch:
                table[f'F{page_num},{gid}'] = ch
                success += 1
            else:
                fail += 1
        except Exception:
            fail += 1

        # Progress + checkpoint every 5s
        now = time.time()
        if now - last_save > 5.0 or i == len(work) - 1:
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(table, f, ensure_ascii=False, indent=2, sort_keys=True)
            elapsed = now - start
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (len(work) - i - 1) / rate if rate > 0 else 0
            print(f"  [{i+1}/{len(work)}] success={success} fail={fail} "
                  f"rate={rate:.1f}/s eta={eta:.0f}s", flush=True)
            last_save = now

    print(f"\nDone: {success} OCR'd, {fail} failed, total in table: {len(table)}", flush=True)


if __name__ == '__main__':
    main()
