#!/usr/bin/env python3
"""
OCR Korean font glyphs using pytesseract (in-process, much faster).
Processes each glyph individually with PSM 10 (single character mode).
"""
import os
import sys
import json
import hashlib

try:
    from PIL import Image
    import pytesseract
except ImportError:
    print("Requires: pip install Pillow pytesseract", file=sys.stderr)
    print("Also: brew install tesseract tesseract-lang", file=sys.stderr)
    sys.exit(1)

FONT_BASE = 0x780000
PAGES = 6
GLYPHS_PER_PAGE = 128
PAGE_SIZE = 0x4000
GLYPH_BYTES = 128
TILE_BYTES = 32
GLYPH_PX = 16
SCALE = 12  # Upscale for OCR


def render_glyph(rom, offset):
    img = Image.new('L', (GLYPH_PX, GLYPH_PX), 0)
    for tile_idx in range(4):
        tx = (tile_idx % 2) * 8
        ty = (tile_idx // 2) * 8
        for row in range(8):
            for px in range(4):
                byte = rom[offset + tile_idx * TILE_BYTES + row * 4 + px]
                p0 = byte & 0x0F
                p1 = (byte >> 4) & 0x0F
                if p0:
                    img.putpixel((tx + px * 2, ty + row), p0 * 17)
                if p1:
                    img.putpixel((tx + px * 2 + 1, ty + row), p1 * 17)
    return img


def is_blank(rom, offset):
    return all(rom[offset + i] == 0 for i in range(GLYPH_BYTES))


def prepare_for_ocr(glyph_img):
    """Scale up glyph and prepare for Tesseract (black text on white bg)."""
    big = glyph_img.resize((GLYPH_PX * SCALE, GLYPH_PX * SCALE), Image.NEAREST)
    pad = GLYPH_PX * SCALE // 2
    result = Image.new('L', (big.width + pad * 2, big.height + pad * 2), 255)
    for y in range(big.height):
        for x in range(big.width):
            v = big.getpixel((x, y))
            if v > 0:
                result.putpixel((x + pad, y + pad), max(0, 255 - v * 2))
    return result


def ocr_single(prepared_img):
    """OCR a single prepared glyph image."""
    # PSM 10 = single character
    text = pytesseract.image_to_string(
        prepared_img, lang='kor', config='--psm 10'
    ).strip()
    hangul = [c for c in text if '\uAC00' <= c <= '\uD7A3']
    if len(hangul) >= 1:
        return hangul[0]

    # Fallback: PSM 8 (single word)
    text2 = pytesseract.image_to_string(
        prepared_img, lang='kor', config='--psm 8'
    ).strip()
    hangul2 = [c for c in text2 if '\uAC00' <= c <= '\uD7A3']
    if len(hangul2) >= 1:
        return hangul2[0]

    return None


def main():
    rom_path = sys.argv[1] if len(sys.argv) > 1 else \
        "Pocket Monsters - LeafGreen (Korean).gba"
    output_json = sys.argv[2] if len(sys.argv) > 2 else \
        ".moneo-artifacts/font-charmap.json"

    with open(rom_path, 'rb') as f:
        rom = f.read()

    charmap = {}
    fingerprints = {}
    total = 0
    recognized = 0
    blanks = 0

    for page in range(PAGES):
        page_label = "F{}".format(page + 1)
        page_rec = 0
        for idx in range(GLYPHS_PER_PAGE):
            offset = FONT_BASE + page * PAGE_SIZE + idx * GLYPH_BYTES
            if is_blank(rom, offset):
                blanks += 1
                continue

            total += 1
            glyph = render_glyph(rom, offset)

            # Fingerprint for cross-referencing with VRAM
            raw = rom[offset:offset + GLYPH_BYTES]
            fp = hashlib.sha256(raw).hexdigest()[:16]
            fingerprints["{},{}".format(page_label, idx)] = fp

            prepared = prepare_for_ocr(glyph)
            char = ocr_single(prepared)

            if char:
                charmap["{},{}".format(page_label, idx)] = char
                recognized += 1
                page_rec += 1

            if total % 50 == 0:
                print("  Progress: {}/{} processed, {} recognized...".format(
                    total, 748, recognized))

        print("Page {}: {}/{} recognized".format(page_label, page_rec, GLYPHS_PER_PAGE))

    # Save
    output = {
        "description": "Korean ROM font charmap: (page,index) -> Unicode",
        "format": "Key = 'F<page>,<index>', page 1-6 (=ROM F1-F6), index 0-127",
        "total_non_blank": total,
        "recognized": recognized,
        "recognition_rate": "{:.1f}%".format(100.0 * recognized / total if total else 0),
        "charmap": charmap,
        "fingerprints": fingerprints
    }

    os.makedirs(os.path.dirname(output_json) or '.', exist_ok=True)
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\nDone: {}/{} glyphs recognized ({:.1f}%)".format(
        recognized, total, 100.0 * recognized / total if total else 0))
    print("Saved: {}".format(output_json))


if __name__ == '__main__':
    main()
