#!/usr/bin/env python3
"""Apply the 2024-02-29 FireRed Korean patch to a Japanese FireRed 1.0 ROM."""
import hashlib, sys
from pathlib import Path

EXPECTED_MD5 = "47596db5a16556c60027e7bf372ec917"
HERE = Path(__file__).resolve().parent
PATCH = HERE / "firered_J-K.xdelta"
DEFAULT_OUT = HERE / "firered_J-K_2024.gba"

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    base_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT
    base = base_path.read_bytes()
    md5 = hashlib.md5(base).hexdigest()
    if md5 != EXPECTED_MD5:
        print(f"WARN: MD5 mismatch ({md5} vs {EXPECTED_MD5})", file=sys.stderr)
    else:
        print(f"OK base MD5: {md5}")
    import xdelta3
    patched = xdelta3.decode(original=base, delta=PATCH.read_bytes())
    out_path.write_bytes(patched)
    print(f"wrote {out_path} ({len(patched):,} bytes)")

if __name__ == "__main__":
    main()
