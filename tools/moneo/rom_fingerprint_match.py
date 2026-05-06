#!/usr/bin/env python3
"""Match ROM (page, idx_byte) pairs to ko_charmap fingerprints to build translation table."""
import hashlib, json, sys
from pathlib import Path

ROM_PATH = "Pocket Monsters - LeafGreen (Korean).gba"
PAGE_TABLE_FILE_OFFSETS = [
    0x081DEEE8 - 0x08000000,  # page 0 (Latin)
    0x08780000 - 0x08000000,  # page 1
    0x08784000 - 0x08000000,  # page 2
    0x08788000 - 0x08000000,  # page 3
    0x0878C000 - 0x08000000,  # page 4
    0x08790000 - 0x08000000,  # page 5
    0x08794000 - 0x08000000,  # page 6
]

def glyph_2bpp_tiles(rom, page, idx_byte):
    page_base = PAGE_TABLE_FILE_OFFSETS[page]
    g = (idx_byte >> 4) * 0x200 + (idx_byte & 0xF) * 0x10
    tl = rom[page_base + g       : page_base + g + 16]
    tr = rom[page_base + g + 16  : page_base + g + 32]
    bl = rom[page_base + g + 256 : page_base + g + 272]
    br = rom[page_base + g + 272 : page_base + g + 288]
    return tl, tr, bl, br

def to_4bpp(tile_16):
    out = bytearray(32)
    for row in range(8):
        left  = tile_16[row * 2 + 1]
        right = tile_16[row * 2 + 0]
        pixels = [(left  >> ((3 - px) * 2)) & 0x3 for px in range(4)] + \
                 [(right >> ((3 - px) * 2)) & 0x3 for px in range(4)]
        for i in range(4):
            out[row * 4 + i] = pixels[i * 2] | (pixels[i * 2 + 1] << 4)
    return bytes(out)

def fingerprint(rom, page, idx_byte):
    tiles = glyph_2bpp_tiles(rom, page, idx_byte)
    raw = b''.join(to_4bpp(t) for t in tiles)
    return hashlib.sha256(raw).hexdigest()[:16]

def main():
    rom = open(ROM_PATH, "rb").read()
    ko = json.loads(Path("app/src/main/assets/moneo/ko_charmap.json").read_text())
    ks = json.loads(Path(".moneo-artifacts/ksx1001-charmap.json").read_text())

    # Build full translation: (page, idx_byte) -> Korean char
    translation = {}  # key "Fp,idx" -> char
    ko_matches = {}

    for page in range(1, 7):
        for idx in range(256):
            fp = fingerprint(rom, page, idx)
            ch = ko.get(fp)
            if ch:
                key = f"F{page},{idx}"
                translation[key] = ch
                ko_matches[(page, idx)] = (fp, ch)

    print(f"ko_charmap matches: {len(ko_matches)} out of {len(ko)}")
    for (p, i), (fp, ch) in sorted(ko_matches.items()):
        print(f"  ROM(p={p},i=0x{i:02X}={i:3d}) fp={fp} = {ch!r}")

    # Also check ksx1001 matches
    print("\nChecking ksx1001-charmap matches...")
    ks_hits = 0
    for page in range(1, 7):
        for idx in range(256):
            fp = fingerprint(rom, page, idx)
            # Try to find in ksx1001 somehow
            # For now just count non-blank glyphs
            tiles = glyph_2bpp_tiles(rom, page, idx)
            raw = b''.join(tiles)
            if any(b != 0 for b in raw):
                ks_hits += 1

    print(f"Non-blank glyphs: {ks_hits}")
    print(f"Translation map size: {len(translation)}")

    # Save as glyph-map.json update (only ko-verified entries for now)
    if translation:
        print(f"\nSaving {len(translation)} verified entries to translation-ko-verified.json")
        Path(".moneo-artifacts/translation-ko-verified.json").write_text(
            json.dumps(translation, ensure_ascii=False, indent=1)
        )

if __name__ == "__main__":
    main()
