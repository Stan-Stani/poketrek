#!/usr/bin/env python3
"""Build a (page, idx) -> Unicode charmap by template-matching ROM glyphs against
reference Hangul syllables rendered with AppleSDGothicNeo at the optimal scale.
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROM_PATH = "Pocket Monsters - LeafGreen (Korean).gba"
FONT_BASE = 0x780000
OUT = ".moneo-artifacts/charmap-v1.json"
KFONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"

with open(ROM_PATH, "rb") as fh:
    ROM = fh.read()


def render_rom(off):
    a = np.zeros((8, 16), dtype=np.float32)
    for dx, to in ((0, 0), (8, 16)):
        for row in range(8):
            for half in range(2):
                b = ROM[off + to + row * 2 + (1 - half)]
                for px in range(4):
                    v = (b >> ((3 - px) * 2)) & 0x3
                    if v:
                        a[row, dx + half * 4 + px] = (0, 1.0, 0.7, 0.4)[v]
    return a


def collect_rom_glyphs():
    glyphs = {}
    for lp in range(12):
        for idx in range(256):
            off = FONT_BASE + lp * 0x2000 + idx * 32
            a = render_rom(off)
            if a.sum() > 0.5:
                glyphs[(lp, idx)] = a
    return glyphs


REF_CHARS = (
    [chr(c) for c in range(0xAC00, 0xD7A4)]
    + list("ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ")
    + list("0123456789!?,.…·′″")
    + list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    + list("abcdefghijklmnopqrstuvwxyz")
    + list("「」『』()[]<>~%/")
)


def render_ref(ch, font, dx, dy, w=16, h=8):
    img = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(img)
    draw.text((dx, dy), ch, fill=255, font=font)
    return np.asarray(img, dtype=np.float32) / 255.0


def score(a, b):
    # Normalized cross-correlation-ish: dot / sqrt(|a|*|b|+eps)
    return float((a * b).sum() / (np.sqrt(a.sum() * b.sum()) + 1e-6))


def find_best_font_params(rom_glyphs, anchors):
    """Find (font_size, dx, dy) maximizing total score on anchor chars."""
    items = list(anchors.items())
    best = None
    for size in range(7, 14):
        font = ImageFont.truetype(KFONT, size)
        for dy in range(-3, 4):
            for dx in range(-2, 3):
                total = 0.0
                for (lp, idx), ch in items:
                    if (lp, idx) not in rom_glyphs:
                        continue
                    rg = rom_glyphs[(lp, idx)]
                    rf = render_ref(ch, font, dx, dy)
                    total += score(rg, rf)
                if best is None or total > best[0]:
                    best = (total, size, dx, dy)
    print(f"best font params: size={best[1]} dx={best[2]} dy={best[3]} total={best[0]:.3f}")
    return best[1], best[2], best[3]


def main():
    print("loading ROM glyphs...")
    rom_glyphs = collect_rom_glyphs()
    print(f"  {len(rom_glyphs)} non-empty")

    # Anchor chars from user-confirmed bytes — page 0
    anchors = {
        (0, 0x10): "가",
        (0, 0x11): "하",
        (0, 0x20): "개",
    }
    size, dx, dy = find_best_font_params(rom_glyphs, anchors)
    font = ImageFont.truetype(KFONT, size)

    # Pre-render all reference templates
    print(f"pre-rendering {len(REF_CHARS)} references...")
    refs = {}
    for ch in REF_CHARS:
        refs[ch] = render_ref(ch, font, dx, dy)

    # Match each ROM glyph
    print("matching...")
    charmap = {}
    confidences = []
    for (lp, idx), rg in rom_glyphs.items():
        best_ch, best_s = None, -1.0
        for ch, rf in refs.items():
            if rf.sum() < 0.5:
                continue
            s = score(rg, rf)
            if s > best_s:
                best_s, best_ch = s, ch
        charmap[f"{lp:X}:{idx:02X}"] = {"ch": best_ch, "score": round(best_s, 3)}
        confidences.append(best_s)

    confidences.sort()
    print(f"score distribution: min={confidences[0]:.3f} p10={confidences[len(confidences)//10]:.3f} "
          f"p50={confidences[len(confidences)//2]:.3f} p90={confidences[len(confidences)*9//10]:.3f} "
          f"max={confidences[-1]:.3f}")

    with open(OUT, "w") as fh:
        json.dump(charmap, fh, ensure_ascii=False, indent=2)
    print(f"wrote {OUT}")

    # Print anchors verification
    for k, expected in anchors.items():
        got = charmap[f"{k[0]:X}:{k[1]:02X}"]
        ok = "✓" if got["ch"] == expected else "✗"
        print(f"  P{k[0]}:{k[1]:02X} expected={expected} got={got['ch']} score={got['score']} {ok}")


if __name__ == "__main__":
    main()
