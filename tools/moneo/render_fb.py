#!/usr/bin/env python3
"""Render mgba_capture framebuffer dumps (240x160 RGBA32) as PNG.

Usage:
  python3 tools/moneo/render_fb.py <fb.bin> <out.png>
  python3 tools/moneo/render_fb.py <dir>            # render all fb-*.bin -> .png siblings
  python3 tools/moneo/render_fb.py --grid <dir> <out.png>  # tile all into one sheet
"""
import os
import sys
from pathlib import Path
from PIL import Image

W, H = 240, 160


def render_one(src: Path, dst: Path) -> None:
    raw = src.read_bytes()
    assert len(raw) == W * H * 4, f"{src}: {len(raw)} bytes"
    # mgba native pixel format: BGRA little-endian (B, G, R, A) on macOS build.
    # Pillow expects RGBA. Swap channels.
    img = Image.frombytes("RGBA", (W, H), raw)
    b, g, r, a = img.split()
    Image.merge("RGBA", (r, g, b, a)).save(dst)


def grid(directory: Path, dst: Path, cols: int = 6, scale: int = 1) -> None:
    fbs = sorted(directory.glob("fb-*.bin"))
    if not fbs:
        print("no fb-*.bin files in", directory)
        sys.exit(1)
    rows = (len(fbs) + cols - 1) // cols
    sheet = Image.new("RGB", (W * cols * scale, H * rows * scale), (0, 0, 0))
    for i, f in enumerate(fbs):
        raw = f.read_bytes()
        img = Image.frombytes("RGBA", (W, H), raw)
        b, g, r, a = img.split()
        img = Image.merge("RGB", (r, g, b))
        if scale != 1:
            img = img.resize((W * scale, H * scale), Image.NEAREST)
        cx = (i % cols) * W * scale
        cy = (i // cols) * H * scale
        sheet.paste(img, (cx, cy))
    sheet.save(dst)
    print(f"wrote {dst} ({len(fbs)} frames, {cols}x{rows})")


def main(argv):
    if len(argv) >= 3 and argv[1] == "--grid":
        grid(Path(argv[2]), Path(argv[3]))
        return
    src = Path(argv[1])
    if src.is_dir():
        for f in sorted(src.glob("fb-*.bin")):
            render_one(f, f.with_suffix(".png"))
        print(f"rendered {len(list(src.glob('fb-*.bin')))} frames in {src}")
        return
    render_one(src, Path(argv[2]))


if __name__ == "__main__":
    main(sys.argv)
