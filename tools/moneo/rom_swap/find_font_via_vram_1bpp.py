#!/usr/bin/env python3
"""Same idea as find_font_via_vram.py, but the font in ROM is likely 1bpp
(8 bytes per 8x8 tile). The renderer expands each bit to a 4-bit nibble
in VRAM. So we collapse each 32-byte VRAM tile down to its 1bpp shape
(pixel set ⇔ nibble != 0) and search ROM for the resulting 8-byte
signature.
"""
from __future__ import annotations
from pathlib import Path

VRAM_DUMP = Path("/tmp/vram_at_title.bin")
ROM = Path(__file__).resolve().parent / "leafgreen_J-K_2024.gba"


def vram_to_1bpp(tile32: bytes) -> bytes:
    """4bpp 8x8 tile (32B) → 1bpp 8x8 tile (8B). Bit set ⇔ nibble != 0."""
    out = bytearray(8)
    for y in range(8):
        bits = 0
        for x in range(0, 8, 2):
            byte = tile32[y * 4 + x // 2]
            lo = byte & 0xF
            hi = (byte >> 4) & 0xF
            if lo:
                bits |= (1 << x)
            if hi:
                bits |= (1 << (x + 1))
        out[y] = bits
    return bytes(out)


def main():
    vram = VRAM_DUMP.read_bytes()
    rom = ROM.read_bytes()
    print(f"VRAM: {len(vram)} bytes, ROM: {len(rom)} bytes")

    # Build the 1bpp tile signatures for every non-blank VRAM tile.
    candidates = []
    for off in range(0, len(vram) - 32, 32):
        tile32 = vram[off:off+32]
        nz = sum(1 for b in tile32 if b != 0)
        if nz < 4 or nz > 30:
            continue
        sig = vram_to_1bpp(tile32)
        nz1 = sum(bin(b).count("1") for b in sig)
        if nz1 < 4 or nz1 > 60:  # skip almost-blank or almost-fill
            continue
        candidates.append((off, tile32, sig))

    print(f"Candidate tiles after 1bpp filtering: {len(candidates)}")

    # Index unique 1bpp signatures
    unique_sigs = {sig: [] for _, _, sig in candidates}
    for vo, _, sig in candidates:
        unique_sigs[sig].append(vo)
    print(f"Unique 1bpp signatures: {len(unique_sigs)}")

    # Search each in the ROM
    sig_to_rom: dict[bytes, list[int]] = {}
    for i, sig in enumerate(unique_sigs):
        if i % 50 == 0:
            print(f"  searching {i}/{len(unique_sigs)}")
        offs = []
        pos = 0
        while True:
            pos = rom.find(sig, pos)
            if pos == -1:
                break
            offs.append(pos)
            pos += 1
        sig_to_rom[sig] = offs

    # Per-tile summary
    matched_total = 0
    matched_patched = 0
    print(f"\n{'vram_off':>8} {'1bpp_hits':>9} {'first':>10} {'last':>10}  region")
    interesting = []
    for vo, _, sig in candidates[:80]:
        offs = sig_to_rom[sig]
        if not offs:
            continue
        matched_total += 1
        in_p = [o for o in offs if 0xD00000 <= o < 0x1000000]
        if in_p:
            matched_patched += 1
            chosen = in_p[0]
            region = "PATCHED"
        else:
            chosen = offs[0]
            region = "VANILLA" if chosen < 0x800000 else "OTHER"
        if len(offs) <= 4:
            print(f"{vo:>8x} {len(offs):>9} {offs[0]:>10x} {offs[-1]:>10x}  {region}")
        interesting.append((vo, sig, offs))

    print(f"\nTiles with any ROM match: {matched_total}/{len(candidates)}")
    print(f"Tiles with patched-region match: {matched_patched}")

    # Look for runs of consecutive VRAM tiles whose 1bpp signature matches at
    # consecutive ROM offsets (stride 8 since 1bpp tile is 8B).
    vram_to_rom = []
    for vo, _, sig in candidates:
        offs = sig_to_rom[sig]
        if not offs:
            continue
        in_p = [o for o in offs if 0xD00000 <= o < 0x1000000]
        chosen = in_p[0] if in_p else offs[0]
        vram_to_rom.append((vo, chosen, len(offs)))

    runs = []
    cur = None
    for vo, ro, hits in vram_to_rom:
        if cur is None:
            cur = [(vo, ro)]
        else:
            pv, pr = cur[-1]
            # vram stride 32, rom stride 8 (1bpp)
            if vo - pv == 32 and ro - pr == 8:
                cur.append((vo, ro))
            else:
                if len(cur) >= 4:
                    runs.append(cur)
                cur = [(vo, ro)]
    if cur and len(cur) >= 4:
        runs.append(cur)
    runs.sort(key=lambda r: -len(r))
    print(f"\n=== Top 20 longest stride runs (vram +32, rom +8) ===")
    for r in runs[:20]:
        v0, r0 = r[0]; v1, r1 = r[-1]
        region = "PATCHED" if r0 >= 0xD00000 else "VANILLA" if r0 < 0x800000 else "OTHER"
        print(f"  len={len(r):>3}  vram={v0:#7x}..{v1:#7x}  rom={r0:#9x}..{r1:#9x}  {region}")

    if runs:
        # Strongest hint: the first ROM offset of the longest patched-region run
        patched_runs = [r for r in runs if r[0][1] >= 0xD00000]
        if patched_runs:
            best = patched_runs[0]
            font_base = best[0][1] - (best[0][0] // 32) * 8
            print(f"\nStrongest patched-region run (len={len(best)}):")
            print(f"  first vram tile {best[0][0]:#x} → ROM {best[0][1]:#x}")
            print(f"  back-extrapolated font_base ≈ {font_base:#x} (ROM file offset)")
            print(f"  GBA address: {0x08000000 + font_base:#x}")


if __name__ == "__main__":
    main()
