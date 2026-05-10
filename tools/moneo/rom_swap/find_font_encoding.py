#!/usr/bin/env python3
"""Try multiple font encodings against VRAM tiles to find the one used by
the 2024 patch. For each encoding, derive an N-byte signature from each
non-blank VRAM tile and search ROM. The encoding with the most hits in
the patched region wins.

Encodings tried:
- 1bpp 8x8 forward         (8 bytes/tile)
- 1bpp 8x8 bit-reversed    (8 bytes/tile)
- 2bpp 8x8 forward         (16 bytes/tile)
- 2bpp 8x8 nibble-swap     (16 bytes/tile, hi/lo nibble swapped)
- Raw 4bpp 8x8             (32 bytes/tile)
"""
from __future__ import annotations
from pathlib import Path

VRAM = Path("/tmp/vram_at_title.bin").read_bytes()
ROM = (Path(__file__).resolve().parent / "leafgreen_J-K_2024.gba").read_bytes()


def to_1bpp(t32: bytes) -> bytes:
    """4bpp → 1bpp: bit set iff nibble != 0."""
    out = bytearray(8)
    for y in range(8):
        bits = 0
        for x in range(0, 8, 2):
            byte = t32[y*4 + x//2]
            if byte & 0x0F: bits |= 1 << x
            if byte & 0xF0: bits |= 1 << (x+1)
        out[y] = bits
    return bytes(out)


def reverse_bits(b: int) -> int:
    b = ((b >> 1) & 0x55) | ((b & 0x55) << 1)
    b = ((b >> 2) & 0x33) | ((b & 0x33) << 2)
    b = ((b >> 4) & 0x0F) | ((b & 0x0F) << 4)
    return b


def to_1bpp_rev(t32: bytes) -> bytes:
    s = to_1bpp(t32)
    return bytes(reverse_bits(b) for b in s)


def to_2bpp(t32: bytes) -> bytes:
    """4bpp → 2bpp: collapse high 2 bits of each nibble."""
    out = bytearray(16)
    for y in range(8):
        # 4 bytes (8 nibbles) per row in 4bpp
        # produce 2 bytes (8 2-bit pixels) per row in 2bpp
        row_bits = 0
        for x in range(8):
            nib = (t32[y*4 + x//2] >> ((x % 2) * 4)) & 0xF
            # 2bpp value: any-nonzero → 1 if nib in {1}, 2 if nib in {2}, 3 if {3,...}
            # simplest: use low 2 bits of nibble
            v = nib & 0x3
            row_bits |= v << (x*2)
        out[y*2]     = row_bits & 0xFF
        out[y*2 + 1] = (row_bits >> 8) & 0xFF
    return bytes(out)


def to_2bpp_alt(t32: bytes) -> bytes:
    """Alternative 2bpp: any nonzero → 1, else 0; pack 8 pixels × 1 bit per row,
    duplicated as plane 1 zero-filled. Common pokémon variant."""
    p0 = bytearray(8)
    p1 = bytearray(8)
    for y in range(8):
        for x in range(8):
            nib = (t32[y*4 + x//2] >> ((x % 2) * 4)) & 0xF
            if nib:
                p0[y] |= 1 << x
            if nib >= 2:
                p1[y] |= 1 << x
    # Interleave like Game Boy 2bpp: p0[y], p1[y], p0[y+1], p1[y+1]...
    out = bytearray(16)
    for y in range(8):
        out[y*2]   = p0[y]
        out[y*2+1] = p1[y]
    return bytes(out)


ENCODINGS = [
    ("1bpp_fwd",  to_1bpp,     8),
    ("1bpp_rev",  to_1bpp_rev, 8),
    ("2bpp",      to_2bpp,     16),
    ("2bpp_gb",   to_2bpp_alt, 16),
]


def search_rom(sig: bytes) -> list[int]:
    out = []
    pos = 0
    while True:
        pos = ROM.find(sig, pos)
        if pos == -1: break
        out.append(pos)
        pos += 1
    return out


def main():
    # Build set of non-blank VRAM tiles
    tiles = []
    for off in range(0, len(VRAM) - 32, 32):
        t = VRAM[off:off+32]
        nz = sum(1 for b in t if b != 0)
        if 4 <= nz <= 30:
            tiles.append((off, t))
    print(f"Non-blank VRAM tiles: {len(tiles)}")

    for name, encoder, sig_len in ENCODINGS:
        print(f"\n=== Encoding: {name} ({sig_len}B sig) ===")
        unique = {}
        for off, t in tiles:
            sig = encoder(t)
            unique.setdefault(sig, []).append(off)
        # Search each unique sig in ROM
        any_match = 0
        patched_match = 0
        runs = []  # (vram_off, rom_off)
        for sig, vrams in unique.items():
            offs = search_rom(sig)
            if not offs:
                continue
            any_match += 1
            in_patched = [o for o in offs if 0xD00000 <= o < 0x1000000]
            if in_patched:
                patched_match += 1
            for vo in vrams:
                chosen = in_patched[0] if in_patched else offs[0]
                runs.append((vo, chosen, len(offs), len(in_patched)))

        print(f"  Unique sigs: {len(unique)}, with any ROM hit: {any_match}, "
              f"with patched hit: {patched_match}")

        # Look for stride runs (vram +32, rom +sig_len)
        runs.sort()
        stride_runs = []
        cur = None
        for vo, ro, *_ in runs:
            if cur is None:
                cur = [(vo, ro)]; continue
            pv, pr = cur[-1]
            if vo - pv == 32 and ro - pr == sig_len:
                cur.append((vo, ro))
            else:
                if len(cur) >= 4: stride_runs.append(cur)
                cur = [(vo, ro)]
        if cur and len(cur) >= 4: stride_runs.append(cur)
        stride_runs.sort(key=lambda r: -len(r))
        if stride_runs:
            print(f"  Top stride-runs:")
            for r in stride_runs[:5]:
                v0, r0 = r[0]; v1, r1 = r[-1]
                region = "PATCHED" if r0 >= 0xD00000 else "VANILLA" if r0 < 0x800000 else "OTHER"
                print(f"    len={len(r):>3}  vram {v0:#x}..{v1:#x}  rom {r0:#x}..{r1:#x}  {region}")
        else:
            print(f"  (no stride runs found)")


if __name__ == "__main__":
    main()
