#!/usr/bin/env python3
"""Build (page, idx) -> Hangul map by template-matching ROM glyphs.

For each ROM glyph slot (page F1..F6, idx 0..255 under pokefirered 16x16 grid
layout), render the glyph as a binary 16x16 pixmap, then score against system
Hangul rendered with AppleSDGothicNeo at the optimal scale/offset.

Output: tools/moneo/glyph-map.json
  { "F1,0": "각", "F1,1": "간", ... }
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROM_PATH = Path("Pocket Monsters - LeafGreen (Korean).gba")
KFONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
OUT_PATH = Path("tools/moneo/glyph-map.json")

FONT_BASE = 0x780000
PAGE_BYTES = 0x4000
NUM_PAGES = 6
PAGE_SLOTS = 256  # text-token addressable slots per page (idx 0..255)

# pokefirered grid layout
def glyph_off(slot: int) -> int:
    row = slot // 16
    col = slot % 16
    return 0x200 * row + 0x20 * col


def render_rom_glyph(rom: bytes, page_base: int, slot: int) -> np.ndarray:
    """Render one ROM glyph as a 16x16 float array in [0,1]."""
    a = np.zeros((16, 16), dtype=np.float32)
    base = page_base + glyph_off(slot)
    for dx, dy, to in [(0, 0, 0), (8, 0, 16), (0, 8, 256), (8, 8, 272)]:
        for r in range(8):
            for half in range(2):
                b = rom[base + to + r * 2 + (1 - half)]
                for px in range(4):
                    v = (b >> ((3 - px) * 2)) & 3
                    if v:
                        # treat any non-zero as "ink"; we use intensity but
                        # binarize for matching (foreground vs background)
                        a[dy + r, dx + half * 4 + px] = 1.0
    return a


def is_blank(rom: bytes, page_base: int, slot: int) -> bool:
    base = page_base + glyph_off(slot)
    for to in (0, 16, 256, 272):
        if any(rom[base + to + i] != 0 for i in range(16)):
            return False
    return True


def render_ref(ch: str, font: ImageFont.FreeTypeFont, dx: int, dy: int) -> np.ndarray:
    img = Image.new("L", (16, 16), 0)
    draw = ImageDraw.Draw(img)
    draw.text((dx, dy), ch, fill=255, font=font)
    a = np.asarray(img, dtype=np.float32) / 255.0
    a = (a > 0.3).astype(np.float32)
    return a


def score(a: np.ndarray, b: np.ndarray) -> float:
    inter = float((a * b).sum())
    union = float((a + b - a * b).sum())
    if union < 1e-6:
        return 0.0
    return inter / union  # IoU


def find_best_font(rom: bytes, refs_per_size: dict) -> tuple[int, int, int]:
    """Coarse search using a few well-known anchors."""
    # Use page F1 idx ranges where we visually confirmed shapes (각/간/갇/갈)
    anchors = {
        (1, 0): "각",
        (1, 1): "간",
        (1, 2): "갇",
        (1, 3): "갈",
    }
    best = None
    for size in range(8, 16):
        for dy in range(-3, 4):
            for dx in range(-2, 3):
                font = ImageFont.truetype(KFONT, size)
                total = 0.0
                for (p, slot), ch in anchors.items():
                    rg = render_rom_glyph(rom, FONT_BASE + (p - 1) * PAGE_BYTES, slot)
                    rf = render_ref(ch, font, dx, dy)
                    total += score(rg, rf)
                if best is None or total > best[0]:
                    best = (total, size, dx, dy)
    print(f"best font: size={best[1]} dx={best[2]} dy={best[3]} total={best[0]:.3f}")
    return best[1], best[2], best[3]


KSX1001_HANGUL: list[str] = []  # filled below


def load_ksx1001() -> list[str]:
    """Load Hangul list from the existing ksx1001-charmap.json (linear order)."""
    p = Path(".moneo-artifacts/ksx1001-charmap.json")
    raw = json.loads(p.read_text(encoding="utf-8"))
    # Keys are F1,0..F1,511, F2,0..F2,511, ..., F5,0..F5,301 = 2350 chars
    pages = {1: 512, 2: 512, 3: 512, 4: 512, 5: 302}
    out = []
    for page, count in pages.items():
        for i in range(count):
            out.append(raw[f"F{page},{i}"])
    return out


def main() -> int:
    rom = ROM_PATH.read_bytes()
    print(f"ROM size: {len(rom)} bytes")

    ksx = load_ksx1001()
    print(f"KSX1001 candidates: {len(ksx)}")

    size, dx, dy = find_best_font(rom, {})
    font = ImageFont.truetype(KFONT, size)

    # Pre-render all reference templates
    refs = []
    for ch in ksx:
        refs.append(render_ref(ch, font, dx, dy))
    refs_arr = np.stack(refs)  # (N, 16, 16)

    # Match each ROM glyph
    out_map: dict[str, str] = {}
    confidences: dict[str, float] = {}
    for page in range(NUM_PAGES):
        page_base = FONT_BASE + page * PAGE_BYTES
        page_label = f"F{page + 1}"
        recognized = 0
        for slot in range(PAGE_SLOTS):
            if is_blank(rom, page_base, slot):
                continue
            rg = render_rom_glyph(rom, page_base, slot)
            # Vectorized IoU over all refs
            inter = (rg[None, :, :] * refs_arr).sum(axis=(1, 2))
            union = (rg[None, :, :] + refs_arr - rg[None, :, :] * refs_arr).sum(axis=(1, 2))
            union = np.maximum(union, 1e-6)
            scores = inter / union
            best = int(np.argmax(scores))
            best_score = float(scores[best])
            if best_score > 0.40:  # min IoU
                key = f"{page_label},{slot}"
                out_map[key] = ksx[best]
                confidences[key] = best_score
                recognized += 1
        print(f"  {page_label}: {recognized} recognized")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps({"map": out_map, "confidence": confidences}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nSaved {OUT_PATH} with {len(out_map)} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
