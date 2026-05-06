#!/usr/bin/env python3
"""Render every (page, idx) glyph from ROM, then OCR with Tesseract Korean.

For each glyph:
  - render 16x16 from ROM at FONT_BASE + page*0x2000 + idx*32
  - upscale 8x with NEAREST so tesseract sees crisp pixels
  - run tesseract with kor language
  - record top candidate + confidence

Output: .moneo-artifacts/glyph-ocr.json
  {"F1,0": {"ch": "글", "conf": 92.3, "alts": ["글", "굴"]}, ...}
"""
import json, subprocess, tempfile, os, re
from pathlib import Path
from PIL import Image
from concurrent.futures import ProcessPoolExecutor, as_completed

ROM = bytes(Path("Pocket Monsters - LeafGreen (Korean).gba").read_bytes())
FONT_BASE = 0x780000
SCALE = 12
WHITE_BG = True


def render_glyph(rom_page: int, idx: int) -> Image.Image:
    off = FONT_BASE + rom_page * 0x2000 + idx * 32
    bg = 255 if WHITE_BG else 0
    fg = 0 if WHITE_BG else 255
    img = Image.new("L", (16, 16), bg)
    p = img.load()
    for row_half in range(2):
        base = off + row_half * 0x100
        for col_half in range(2):
            tile_off = base + col_half * 0x10
            for row in range(8):
                byte_off = tile_off + row * 2
                if byte_off + 1 >= len(ROM):
                    continue
                for half in range(2):
                    b = ROM[byte_off + (1 - half)]  # left-half is byte+1
                    for px in range(4):
                        v = (b >> ((3 - px) * 2)) & 0x3
                        x = col_half * 8 + half * 4 + px
                        y = row_half * 8 + row
                        if v:
                            # body=fg, shadow=mid
                            shade = fg if v >= 1 else (128 if WHITE_BG else 128)
                            p[x, y] = shade
    return img


def is_blank(img: Image.Image) -> bool:
    px = list(img.getdata())
    if WHITE_BG:
        return all(v >= 240 for v in px)
    return all(v <= 15 for v in px)


def ocr_one(args):
    p, idx = args
    img = render_glyph(p, idx)
    if is_blank(img):
        return (p, idx, None, 0.0, [])
    big = img.resize((16 * SCALE, 16 * SCALE), Image.NEAREST)
    # Add white border for tesseract
    bordered = Image.new("L", (big.width + 40, big.height + 40), 255 if WHITE_BG else 0)
    bordered.paste(big, (20, 20))
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tf:
        bordered.save(tf.name)
        tmp_path = tf.name
    try:
        out = subprocess.run(
            ['tesseract', tmp_path, '-', '-l', 'kor',
             '--psm', '10', '-c', 'tessedit_char_whitelist='],
            capture_output=True, text=True, timeout=10)
        text = out.stdout.strip()
        # Pick first hangul char
        ch = None
        for c in text:
            if '\uAC00' <= c <= '\uD7A3':
                ch = c; break
        return (p, idx, ch, 0.0, list(text))
    except Exception as e:
        return (p, idx, None, 0.0, [])
    finally:
        os.unlink(tmp_path)


def main():
    candidates = [(p, i) for p in range(1, 7) for i in range(256)]
    print(f"Total candidates: {len(candidates)}")

    # Render once to identify blanks
    blanks = 0
    nonblank = []
    for p, i in candidates:
        if is_blank(render_glyph(p, i)):
            blanks += 1
        else:
            nonblank.append((p, i))
    print(f"Blanks: {blanks}, nonblank: {len(nonblank)}")

    results = {}
    with ProcessPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(ocr_one, (p, i)): (p, i) for (p, i) in nonblank}
        done = 0
        for fut in as_completed(futures):
            p, i, ch, conf, alts = fut.result()
            done += 1
            if ch:
                results[f"F{p},{i}"] = {"ch": ch, "alts": alts}
            if done % 100 == 0:
                print(f"  progress: {done}/{len(nonblank)}, mapped {len(results)}")

    Path('.moneo-artifacts/glyph-ocr.json').write_text(
        json.dumps(results, ensure_ascii=False, indent=1))
    print(f"\nMapped {len(results)} / {len(nonblank)} non-blank glyphs")
    print("Wrote .moneo-artifacts/glyph-ocr.json")


if __name__ == "__main__":
    main()
