#!/usr/bin/env python3
"""Interactive glyph labeling tool for moneo.

Shows each unlabeled non-trivial glyph as Unicode block art in your terminal,
prompts for the Hangul character, saves progress incrementally.

Usage:
  python3 tools/moneo/label_glyphs.py            # label all unlabeled glyphs
  python3 tools/moneo/label_glyphs.py --review   # also show currently-labeled ones
  python3 tools/moneo/label_glyphs.py --page 4   # only page 4

Controls (press Enter after each):
  <hangul>   save the label and advance
  (blank)    skip this glyph (mark unknown, advance)
  s          stop / save and quit
  u          undo last entry
  ?          show progress + remaining count

Saves to tools/moneo/glyph-map.json after every label (no work lost on Ctrl-C).
"""
from __future__ import annotations
import argparse
import json
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)
from decoded_blit import transform_glyph

ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
ROM_PATH = os.path.join(ROOT, "Pocket Monsters - LeafGreen (Korean).gba")
GMAP_PATH = os.path.join(_THIS_DIR, "glyph-map.json")


def load_rom() -> bytes:
    with open(ROM_PATH, "rb") as f:
        return f.read()


def load_gmap():
    with open(GMAP_PATH) as f:
        d = json.load(f)
    return d


def save_gmap(d):
    with open(GMAP_PATH, "w") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def is_blank_glyph(rom: bytes, p: int, i: int) -> bool:
    """All pixels are 0 or 1 (no actual glyph content)."""
    bs = transform_glyph(rom, p, i)
    return not any(
        ((b & 0xF) not in (0, 1)) or (((b >> 4) & 0xF) not in (0, 1))
        for b in bs
    )


def render_terminal(rom: bytes, p: int, i: int) -> str:
    """Render glyph as 8 rows × 16 cols of Unicode block chars (1 char per 2 px row)."""
    bs = transform_glyph(rom, p, i)
    # Build 16x16 nibble grid in standard tile layout.
    grid = [[0] * 16 for _ in range(16)]
    for k, (sx, sy) in enumerate([(0, 0), (8, 0), (0, 8), (8, 8)]):
        sub = bs[k * 32 : (k + 1) * 32]
        for r in range(8):
            for c in range(8):
                b = sub[r * 4 + c // 2]
                v = ((b >> 4) & 0xF) if (c & 1) else (b & 0xF)
                grid[sy + r][sx + c] = v

    def is_filled(v: int) -> bool:
        return v in (2, 3)  # glyph dark or mid

    rows = []
    for ry in range(0, 16, 2):
        chars = []
        for cx in range(16):
            top = is_filled(grid[ry][cx])
            bot = is_filled(grid[ry + 1][cx]) if ry + 1 < 16 else False
            if top and bot:
                chars.append("█")
            elif top:
                chars.append("▀")
            elif bot:
                chars.append("▄")
            else:
                chars.append(" ")
        rows.append("".join(chars))
    return "\n".join(rows)


def is_hangul(c: str) -> bool:
    return len(c) == 1 and "가" <= c <= "힣"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", action="store_true", help="include already-labeled")
    ap.add_argument("--page", type=int, choices=range(1, 7), help="only this page")
    args = ap.parse_args()

    rom = load_rom()
    gmap_doc = load_gmap()
    labels = dict(gmap_doc["map"])

    queue = []
    for p in range(1, 7):
        if args.page and p != args.page:
            continue
        for i in range(256):
            key = f"F{p},{i}"
            if is_blank_glyph(rom, p, i):
                continue
            if not args.review and key in labels:
                continue
            queue.append((p, i, key))
    total = len(queue)
    if total == 0:
        print("Nothing to label. Use --review to relabel existing entries.")
        return

    print(f"\n  {total} glyphs to label.")
    print("  Type Hangul + Enter to save. Empty Enter to skip.")
    print("  Commands: 's' stop, 'u' undo, '?' status\n")

    history = []
    n = 0
    skipped = 0
    while n < len(queue):
        p, i, key = queue[n]
        existing = labels.get(key, "")
        existing_str = f"  (currently: {existing})" if existing else ""
        print()
        print(f"┌─ glyph {n+1}/{total}  •  page {p}  idx {i}  •  key {key}{existing_str}")
        print("│")
        for line in render_terminal(rom, p, i).splitlines():
            print(f"│  {line}")
        print("│")
        try:
            ans = input("└─ label > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[saved + exiting]")
            break

        if ans == "s":
            print("[saved + exiting]")
            break
        if ans == "?":
            print(f"   progress: {n}/{total} done, {skipped} skipped")
            continue
        if ans == "u":
            if not history:
                print("   nothing to undo.")
                continue
            prev_n, prev_key, prev_label = history.pop()
            n = prev_n
            if prev_label is None:
                labels.pop(prev_key, None)
            else:
                labels[prev_key] = prev_label
            gmap_doc["map"] = dict(sorted(labels.items(), key=lambda kv: tuple(int(x) for x in kv[0][1:].split(","))))
            save_gmap(gmap_doc)
            print(f"   undone: {prev_key}")
            continue
        if ans == "":
            history.append((n, key, labels.get(key)))
            skipped += 1
            n += 1
            continue
        if not all(is_hangul(c) for c in ans):
            print(f"   '{ans}' is not pure Hangul. Try again or skip with empty Enter.")
            continue
        history.append((n, key, labels.get(key)))
        labels[key] = ans
        gmap_doc["map"] = dict(sorted(labels.items(), key=lambda kv: tuple(int(x) for x in kv[0][1:].split(","))))
        save_gmap(gmap_doc)
        n += 1

    print(f"\nDone. {n} processed, {skipped} skipped. Total labels: {len(labels)}")


if __name__ == "__main__":
    main()
