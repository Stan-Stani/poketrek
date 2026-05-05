#!/usr/bin/env python3
"""Compute (page, idx) -> VRAM fingerprint via the live blit table, then check
overlap against fingerprints actually observed in live capture VRAM groups.

This validates the blit logic itself (independent of any prior char labels)."""
from __future__ import annotations
import hashlib, json, struct
from itertools import permutations
from pathlib import Path

ROM = bytes(Path("Pocket Monsters - LeafGreen (Korean).gba").read_bytes())
IWRAM = bytes(Path(".moneo-artifacts/dumps/iwram.bin").read_bytes())
FONT_BASE = 0x780000

table1 = ROM[0x1CDF1C : 0x1CDF1C + 256]
table2 = struct.unpack_from("<256H", IWRAM, 0x0A40)


def blit_byte(rb: int) -> int:
    return table2[table1[rb]]


def blit_tile(rom_off: int, hi_first: bool) -> bytes:
    out = bytearray(32)
    for hw in range(8):
        b0 = ROM[rom_off + hw * 2]
        b1 = ROM[rom_off + hw * 2 + 1]
        first, second = (b1, b0) if hi_first else (b0, b1)
        v0 = blit_byte(first)
        v1 = blit_byte(second)
        out[hw * 4 + 0] = v0 & 0xFF
        out[hw * 4 + 1] = (v0 >> 8) & 0xFF
        out[hw * 4 + 2] = v1 & 0xFF
        out[hw * 4 + 3] = (v1 >> 8) & 0xFF
    return bytes(out)


def glyph_offsets(rom_page: int, idx: int):
    base = FONT_BASE + rom_page * 0x2000 + idx * 32
    return [base + 0, base + 16, base + 256, base + 272]


def main():
    cap = json.loads(Path(".moneo-artifacts/capture-long2.json").read_text())
    live_fps = set()
    for g in cap.get("groups", []):
        for fp in g.get("fps", []):
            live_fps.add(fp)
    print(f"live unique fps: {len(live_fps)}")

    candidates = [(p, i) for p in range(1, 7) for i in range(256)]

    # Try every sub-tile permutation × byte-order × hash-length
    best = None
    for perm in permutations(range(4)):
        for hi_first in (False, True):
            fps_pi = {}
            for (p, i) in candidates:
                offs = glyph_offsets(p, i)
                parts = [blit_tile(offs[k], hi_first) for k in perm]
                blob = b"".join(parts)
                fp = hashlib.sha256(blob).hexdigest()[:16]
                fps_pi[(p, i)] = fp
            hits = sum(1 for fp in fps_pi.values() if fp in live_fps)
            if best is None or hits > best[0]:
                best = (hits, perm, hi_first, fps_pi)
                if hits > 50:
                    print(f"  perm={perm} hi_first={hi_first} -> hits={hits}")
    hits, perm, hi_first, fps_pi = best
    print(f"\nBest: perm={perm} hi_first={hi_first} hits={hits}/{len(live_fps)} live fps")

    # Save (page, idx) -> fp map
    out = {
        "perm": list(perm),
        "hi_first": hi_first,
        "live_fps_total": len(live_fps),
        "matched": hits,
        "fp_by_pi": {f"F{p},{i}": fps_pi[(p, i)] for (p, i) in candidates},
    }
    Path(".moneo-artifacts/blit-fp-live.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1)
    )
    print("Wrote .moneo-artifacts/blit-fp-live.json")


if __name__ == "__main__":
    main()
