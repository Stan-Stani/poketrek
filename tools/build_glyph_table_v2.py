#!/usr/bin/env python3
"""
build_glyph_table_v2.py — Higher-quality OCR pass.

Renders glyphs at multiple scales with smoothing and runs Tesseract with
multiple PSM modes; picks the best result by confidence score.
"""
import os
import sys
import json
import time

try:
    from PIL import Image, ImageFilter
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


def render_raw(rom, base, gid):
    """Render at 16x16 native resolution, grayscale."""
    o = base + goff(gid)
    img = Image.new('L', (16, 16), 255)
    levels = [255, 0, 80, 160]  # 0=transparent (white bg), 1=black, 2=dark, 3=light
    for dx, dy, toff in [(0, 0, 0), (8, 0, 16), (0, 8, 256), (8, 8, 272)]:
        for row in range(8):
            left = rom[o + toff + row * 2 + 1]
            right = rom[o + toff + row * 2 + 0]
            for px in range(4):
                vL = (left >> ((3 - px) * 2)) & 0x3
                vR = (right >> ((3 - px) * 2)) & 0x3
                if vL:
                    img.putpixel((dx + px, dy + row), levels[vL])
                if vR:
                    img.putpixel((dx + 4 + px, dy + row), levels[vR])
    return img


def prep_for_ocr(raw, scale=20):
    """Upscale with smoothing + padding for Tesseract."""
    big = raw.resize((16 * scale, 16 * scale), Image.LANCZOS)
    pad = scale * 6
    out = Image.new('L', (big.width + pad * 2, big.height + pad * 2), 255)
    out.paste(big, (pad, pad))
    return out


def ocr_glyph(img):
    """Try multiple PSM modes and return best Hangul char with confidence."""
    best = (None, -1)
    for psm in (10, 8, 7, 6):
        cfg = f'--psm {psm} --oem 1'
        try:
            data = pytesseract.image_to_data(
                img, lang='kor', config=cfg,
                output_type=pytesseract.Output.DICT,
            )
            for i, txt in enumerate(data['text']):
                if not txt:
                    continue
                conf = float(data['conf'][i])
                for c in txt:
                    if '\uAC00' <= c <= '\uD7A3':
                        if conf > best[1]:
                            best = (c, conf)
                        break
                    if '\u3130' <= c <= '\u318F':
                        if conf > best[1]:
                            best = (c, conf)
                        break
        except Exception:
            continue
    return best


def main():
    with open(ROM, 'rb') as f:
        rom = f.read()

    os.makedirs(ART, exist_ok=True)
    out_path = os.path.join(ART, 'glyph-table-v2.json')

    table = {}
    if os.path.exists(out_path):
        try:
            with open(out_path, encoding='utf-8') as f:
                table = json.load(f)
            print(f"Resuming with {len(table)} existing", flush=True)
        except Exception:
            pass

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

    print(f"To OCR: {len(work)}", flush=True)

    start = time.time()
    last_save = start
    success = 0

    for i, (page_num, gid, base) in enumerate(work):
        raw = render_raw(rom, base, gid)
        img = prep_for_ocr(raw)
        ch, conf = ocr_glyph(img)
        if ch:
            table[f'F{page_num},{gid}'] = {'char': ch, 'conf': conf}
            success += 1

        now = time.time()
        if now - last_save > 5.0 or i == len(work) - 1:
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(table, f, ensure_ascii=False, indent=2, sort_keys=True)
            elapsed = now - start
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (len(work) - i - 1) / rate if rate > 0 else 0
            print(f"  [{i+1}/{len(work)}] success={success} "
                  f"rate={rate:.1f}/s eta={eta:.0f}s", flush=True)
            last_save = now

    print(f"Done: {success}/{len(work)}", flush=True)


if __name__ == '__main__':
    main()
