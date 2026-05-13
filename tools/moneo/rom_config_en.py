"""Centralized offsets + path for the canonical English LeafGreen ROM.

Sibling of `rom_config.py` (Korean 2024 patch). Used by the EN ROM scanner
and the EN name-table extractor so the moneo gloss pipeline can pair each
ROM-anchored Korean entry with its in-game English equivalent.

Offsets verified empirically by `find_offsets_en.py` against the on-disk
`Pokemon - LeafGreen Version (USA, Europe) (Rev 1).gba` (CRC `0xDAFFECEC`,
gamecode `BPGE`). They happen to match the Korean 2024 patch values
because the patch was rebuilt over the canonical FRLG layout — but the
match is not load-bearing here; if the EN ROM ever changes, only this
file needs updating.
"""
from __future__ import annotations
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
ROOT = THIS_DIR.parents[1]

ROM_PATH_EN = ROOT / "Pokemon - LeafGreen Version (USA, Europe) (Rev 1).gba"
ROM_CRC32_EN = 0xDAFFECEC
ROM_GAMECODE_EN = "BPGE"

GBA_BASE = 0x08000000

# === Name tables (verified by find_offsets_en.py) ===
GMOVE_NAMES_EN = 0x2470E0
GMOVE_NAMES_EN_STRIDE = 13
GMOVE_NAMES_EN_N = 355

GABILITY_NAMES_EN = 0x24FC8C
GABILITY_NAMES_EN_STRIDE = 13
GABILITY_NAMES_EN_N = 78

GSPECIES_NAMES_EN = 0x245F2C
GSPECIES_NAMES_EN_STRIDE = 11
GSPECIES_NAMES_EN_N = 412

GITEMS_EN = 0x3DAED4
GITEMS_EN_STRIDE = 44
GITEMS_EN_NAME_OFF = 0
GITEMS_EN_N = 375

GPOKEDEX_ENTRIES_EN = 0x44E2E0
GPOKEDEX_EN_STRIDE = 36
GPOKEDEX_EN_CATEGORY_OFF = 0    # categoryName[12] is the first field
GPOKEDEX_EN_N = 387

GTRAINER_CLASS_NAMES_EN = 0x23E5A4
GTRAINER_CLASS_NAMES_EN_STRIDE = 13
GTRAINER_CLASS_NAMES_EN_N = 107


# === Gen 3 English character set (Bulbapedia: Character encoding (Gen III)) ===
# Single-byte mapping for printable ASCII; multi-byte escapes are handled by
# the scanner as inline control codes (0xFC, 0xFD, 0xFE).
def _build_charmap() -> dict[int, str]:
    m: dict[int, str] = {0x00: " "}
    for i, c in enumerate("0123456789"):     m[0xA1 + i] = c
    for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"): m[0xBB + i] = c
    for i, c in enumerate("abcdefghijklmnopqrstuvwxyz"): m[0xD5 + i] = c
    m[0xAB] = "!"
    m[0xAC] = "?"
    m[0xAD] = "."
    m[0xAE] = "-"
    m[0xB0] = "…"   # ellipsis
    m[0xB1] = "“"
    m[0xB2] = "”"
    m[0xB3] = "‘"
    m[0xB4] = "’"
    m[0xB5] = "♂"
    m[0xB6] = "♀"
    m[0xB8] = ","
    m[0xBA] = "/"
    m[0xF0] = ":"
    m[0x1B] = "é"   # POKéMON
    m[0x1C] = "É"
    return m


EN_CHARMAP: dict[int, str] = _build_charmap()
EN_CHARMAP_INV: dict[str, int] = {v: k for k, v in EN_CHARMAP.items()}

# Terminator + control bytes.
#   0xFF      end-of-string
#   0xFA/B/E  single-byte newline / paragraph-delay / scroll-prompt
#   0xFC/D    two-byte controls (prefix + 1-byte id, for {COLOR x}, {PLAYER}, …)
EN_END_MARKER = 0xFF
EN_NEWLINE_BYTES = {0xFA, 0xFB, 0xFE}
EN_INLINE_PREFIXES_WITH_ARG = {0xFC, 0xFD}
