#!/usr/bin/env python3
"""LZ77-decompress each patched-region candidate and dump diagnostics.

GBA-standard LZ77 (compression type 0x10): 4-byte header
  byte 0:  0x10
  bytes 1-3: uncompressed size (little-endian, 24-bit)
Body: blocks of (1 flag byte + 8 chunks). Each chunk is either an uncompressed
byte, or a 16-bit BE back-reference: top 4 bits = match_len-3, low 12 bits =
displacement-1.
"""
from __future__ import annotations
from pathlib import Path

ROM = Path(__file__).resolve().parent / "leafgreen_J-K_2024.gba"
GBA_BASE = 0x08000000


def lz77_decompress(data: bytes, offset: int) -> bytes | None:
    if offset + 4 > len(data) or data[offset] != 0x10:
        return None
    size = data[offset + 1] | (data[offset + 2] << 8) | (data[offset + 3] << 16)
    if size > 0x40000:
        return None  # sanity cap: 256 KB
    src = offset + 4
    out = bytearray()
    while len(out) < size:
        if src >= len(data):
            return None
        flags = data[src]; src += 1
        for bit in range(8):
            if len(out) >= size:
                break
            if (flags & (0x80 >> bit)) == 0:
                if src >= len(data):
                    return None
                out.append(data[src]); src += 1
            else:
                if src + 1 >= len(data):
                    return None
                hi = data[src]; lo = data[src + 1]; src += 2
                length = (hi >> 4) + 3
                disp = ((hi & 0x0F) << 8) | lo
                pos = len(out) - disp - 1
                if pos < 0:
                    return None
                for _ in range(length):
                    out.append(out[pos]); pos += 1
    return bytes(out[:size])


def hex_preview(b: bytes, width: int = 32, lines: int = 8) -> str:
    out = []
    for i in range(0, min(len(b), width * lines), width):
        chunk = b[i:i+width]
        out.append(f"  {i:04x}: " + " ".join(f"{x:02x}" for x in chunk))
    return "\n".join(out)


def tile4bpp_density(b: bytes) -> tuple[int, int, int]:
    """Per-tile (32 bytes) density stats for 4bpp data: tile_count, mean_nonzero%, std."""
    if len(b) < 32:
        return 0, 0, 0
    n = len(b) // 32
    densities = []
    for i in range(n):
        tile = b[i*32:(i+1)*32]
        nonzero = sum(1 for byte in tile if byte != 0)
        densities.append(nonzero / 32)
    mean = sum(densities) / n
    var = sum((d - mean) ** 2 for d in densities) / n
    return n, int(mean * 100), int(var ** 0.5 * 100)


def main():
    data = ROM.read_bytes()
    candidates = [
        ("primary",  0x8e98164),
        ("alt1",     0x8e9cb60),
        ("alt2",     0x8eb8854),
        ("alt3",     0x8e9b52c),
        ("alt4",     0x8e9b464),
        ("alt5",     0x8eb0e24),
    ]
    print(f"{'label':>8} {'gba_addr':>10} {'file_off':>10} {'header':>6} "
          f"{'usize':>6} {'tiles':>6} {'nz%':>4} {'std':>4}  notes")
    out_dir = Path(__file__).resolve().parent / "lz77_candidates_2024"
    out_dir.mkdir(exist_ok=True)
    for label, gba in candidates:
        off = gba - GBA_BASE
        hdr = data[off]
        size = data[off+1] | (data[off+2] << 8) | (data[off+3] << 16)
        decomp = lz77_decompress(data, off)
        if decomp is None:
            print(f"{label:>8} {gba:>10x} {off:>10x} {hdr:>6x} {size:>6x}  ❌ decompression failed")
            continue
        n, dens, std = tile4bpp_density(decomp)
        # First 32 bytes preview
        notes = ""
        if dens < 5:
            notes = "mostly empty"
        elif dens > 90:
            notes = "mostly filled (palette/tilemap?)"
        elif std > 10:
            notes = "varying density (tile-like)"
        print(f"{label:>8} {gba:>10x} {off:>10x} {hdr:>6x} {size:>6x} {n:>6} {dens:>4} {std:>4}  {notes}")
        # Save raw decompressed
        out_file = out_dir / f"{label}_{gba:08x}.bin"
        out_file.write_bytes(decomp)

    print(f"\nDecompressed bins saved to {out_dir}/")
    print()
    print("=== Hex previews ===")
    for label, gba in candidates:
        off = gba - GBA_BASE
        decomp = lz77_decompress(data, off)
        if decomp is None:
            continue
        print(f"\n--- {label} @ {gba:#x} (uncompressed {len(decomp)} bytes) ---")
        print(hex_preview(decomp, 32, 4))


if __name__ == "__main__":
    main()
