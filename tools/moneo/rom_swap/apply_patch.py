#!/usr/bin/env python3
"""Apply the 2024-02-29 xdelta patch to a Japanese FRLG ROM.

Required base: Pocket Monsters - LeafGreen (Japan) 1.0
  MD5 must be 138a71a5be83f3f3d7af3d31916a5fc7

Usage:
  python3 apply_patch.py <japanese_leafgreen.gba> [output_path]

Output defaults to: tools/moneo/rom_swap/leafgreen_J-K_2024.gba
"""
import hashlib
import sys
from pathlib import Path

EXPECTED_MD5 = "138a71a5be83f3f3d7af3d31916a5fc7"
HERE = Path(__file__).resolve().parent
PATCH = HERE / "leafgreen_J-K.xdelta"
DEFAULT_OUT = HERE / "leafgreen_J-K_2024.gba"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    base_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT

    if not base_path.exists():
        print(f"ERROR: base ROM not found at {base_path}", file=sys.stderr)
        sys.exit(2)

    base = base_path.read_bytes()
    md5 = hashlib.md5(base).hexdigest()
    if md5 != EXPECTED_MD5:
        print(f"WARNING: base ROM MD5 = {md5}", file=sys.stderr)
        print(f"  expected: {EXPECTED_MD5}", file=sys.stderr)
        print(f"  patch may fail with XD3_INVALID_INPUT.", file=sys.stderr)
        # continue anyway
    else:
        print(f"OK base MD5 matches: {md5}")

    import xdelta3
    patch = PATCH.read_bytes()
    print(f"applying {PATCH.name} ({len(patch):,} bytes) to base ({len(base):,} bytes)...")
    patched = xdelta3.decode(input_bytes=patch, source_bytes=base)
    out_path.write_bytes(patched)
    print(f"wrote {out_path} ({len(patched):,} bytes)")


if __name__ == "__main__":
    main()
