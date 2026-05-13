#!/usr/bin/env python3
"""Extract English name tables from the canonical EN LeafGreen ROM.

Decode-only. Emits a flat dictionary keyed by source-tag (e.g.
`"gMoveNames"`, `"gItems"`) that the gloss pipeline pairs against each
Korean ROM-anchored entry's `source` field.

Output: `tools/moneo/name_tables_en.json`
```json
{
  "rom_crc32": "0xDAFFECEC",
  "tables": {
    "gMoveNames":    {"1": "Pound", "2": "Karate Chop", ...},
    "gAbilityNames": {"1": "Stench", ...},
    "gSpeciesNames": {"1": "Bulbasaur", ...},
    "gItems":        {"1": "Master Ball", ...},
    "gPokedexEntries.category": {"1": "Seed", ...}
  }
}
```

Title-cases the ALL-CAPS values from the ROM so the on-card gloss reads
like prose ("Pound", not "POUND") — that matches how every other Pokémon
gloss in the project is rendered.
"""
from __future__ import annotations
import json
import sys
import zlib
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))
from rom_config_en import (  # noqa: E402
    ROM_PATH_EN, ROM_CRC32_EN,
    GMOVE_NAMES_EN, GMOVE_NAMES_EN_STRIDE, GMOVE_NAMES_EN_N,
    GABILITY_NAMES_EN, GABILITY_NAMES_EN_STRIDE, GABILITY_NAMES_EN_N,
    GSPECIES_NAMES_EN, GSPECIES_NAMES_EN_STRIDE, GSPECIES_NAMES_EN_N,
    GITEMS_EN, GITEMS_EN_STRIDE, GITEMS_EN_NAME_OFF, GITEMS_EN_N,
    GPOKEDEX_ENTRIES_EN, GPOKEDEX_EN_STRIDE, GPOKEDEX_EN_CATEGORY_OFF, GPOKEDEX_EN_N,
    EN_CHARMAP, EN_END_MARKER, EN_NEWLINE_BYTES, EN_INLINE_PREFIXES_WITH_ARG,
)

OUT = THIS_DIR / "name_tables_en.json"


def decode_string(rom: bytes, off: int, max_len: int) -> str:
    """Walk one Gen 3 EN string. Stops at 0xFF; emits placeholders for
    inline control codes (0xFC<id>, 0xFD<id>, 0xFE<id>).
    """
    out: list[str] = []
    i = 0
    while i < max_len:
        b = rom[off + i]
        if b == EN_END_MARKER:
            break
        if b in EN_NEWLINE_BYTES:
            # Newlines shouldn't appear inside name strings, but consume
            # defensively rather than emitting a literal "\n" in a gloss.
            i += 1
            continue
        if b in EN_INLINE_PREFIXES_WITH_ARG:
            i += 2
            continue
        ch = EN_CHARMAP.get(b)
        if ch is None:
            # Out-of-charmap byte — emit a hex placeholder so corrupt
            # entries are visible without aborting the whole table.
            out.append(f"\\x{b:02X}")
        else:
            out.append(ch)
        i += 1
    return "".join(out).rstrip()


def titlecase(s: str) -> str:
    """ROM strings are ALL CAPS. Convert to natural title case while
    preserving symbols, single-char tokens (e.g. "TM01"), and the
    ♂/♀ glyphs.

    "MASTER BALL"  -> "Master Ball"
    "KARATE CHOP"  -> "Karate Chop"
    "NIDORAN♂"     -> "Nidoran♂"
    "HP UP"        -> "Hp Up"   (acceptable; pure-acronym tokens are rare)
    """
    parts = s.split(" ")
    return " ".join(p[:1] + p[1:].lower() if p else p for p in parts)


def extract_table(rom: bytes, off: int, stride: int, n: int,
                  name_field_off: int = 0, name_field_len: int | None = None) -> dict[str, str]:
    out: dict[str, str] = {}
    width = name_field_len if name_field_len is not None else stride
    # Skip index 0 (placeholder) — start at 1 so the dict aligns with
    # pokefirered constant indexing (MOVE_POUND=1 etc.).
    for i in range(1, n):
        entry_off = off + i * stride + name_field_off
        raw = decode_string(rom, entry_off, width)
        if not raw:
            continue
        out[str(i)] = titlecase(raw)
    return out


def main() -> int:
    rom = ROM_PATH_EN.read_bytes()
    crc = zlib.crc32(rom)
    if crc != ROM_CRC32_EN:
        print(f"FAIL: ROM CRC mismatch: 0x{crc:08X} != 0x{ROM_CRC32_EN:08X}", file=sys.stderr)
        return 1

    tables = {
        "gMoveNames":               extract_table(rom, GMOVE_NAMES_EN, GMOVE_NAMES_EN_STRIDE, GMOVE_NAMES_EN_N),
        "gAbilityNames":            extract_table(rom, GABILITY_NAMES_EN, GABILITY_NAMES_EN_STRIDE, GABILITY_NAMES_EN_N),
        "gSpeciesNames":            extract_table(rom, GSPECIES_NAMES_EN, GSPECIES_NAMES_EN_STRIDE, GSPECIES_NAMES_EN_N),
        "gItems":                   extract_table(rom, GITEMS_EN, GITEMS_EN_STRIDE, GITEMS_EN_N,
                                                  name_field_off=GITEMS_EN_NAME_OFF, name_field_len=14),
        "gPokedexEntries.category": extract_table(rom, GPOKEDEX_ENTRIES_EN, GPOKEDEX_EN_STRIDE, GPOKEDEX_EN_N,
                                                  name_field_off=GPOKEDEX_EN_CATEGORY_OFF, name_field_len=12),
    }
    doc = {
        "rom_crc32": f"0x{ROM_CRC32_EN:08X}",
        "rom_path":  str(ROM_PATH_EN.relative_to(THIS_DIR.parents[1])),
        "generator": "build_name_table_decks_en.py",
        "tables":    tables,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    for table, entries in tables.items():
        print(f"  {table:30s} {len(entries):4d} entries  [1]={entries.get('1')!r}")
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
