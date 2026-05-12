#!/usr/bin/env python3
"""Add every entry of the stride-indexed name tables (gMoveNames,
gAbilityNames, gSpeciesNames, gTrainerClassNames, gItems names) as
individual records in corpus.ko.json.

scan_rom_2024.py only decodes targets that are explicitly pointer-
literal'd from somewhere in the ROM. Stride-indexed tables, where each
entry's address is computed (base + i*stride) rather than stored as
an independent pointer, get only the FIRST entry picked up.

Adds the missing entries so:
  - Words like 막치기, 태권당수 are present in corpus.ko.json
  - Lemma_index can tokenize them and produce vocab cards
  - Source-type tagging from these records can flag them as
    'pokemon_move'/'pokemon_ability'/'pokemon_species'/'trainer_class'

These records get a synthetic 'source' field naming the table
(e.g. 'gMoveNames[3]') so downstream tools can identify them.
"""
from __future__ import annotations
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CORPUS = ROOT / "app/src/main/assets/moneo/corpus.ko.json"
ROM_PATH = HERE / "rom_swap/leafgreen_J-K_2024.gba"
CODEPOINT_MAP = HERE / "rom_swap/codepoint_map.json"

sys.path.insert(0, str(HERE))
from rom_config import (  # noqa: E402
    GTRAINER_CLASS_NAMES, GITEMS, GITEMS_STRIDE, GITEMS_NAME_OFF,
)

# Match build_name_table_decks.py constants
GMOVE_NAMES = 0x2470E0;    GMOVE_NAMES_STRIDE = 13;    GMOVE_NAMES_N = 355
GABILITY_NAMES = 0x24FC8C; GABILITY_NAMES_STRIDE = 13; GABILITY_NAMES_N = 78
GSPECIES_NAMES = 0x245F2C; GSPECIES_NAMES_STRIDE = 11; GSPECIES_NAMES_N = 412
GTRAINER_CLASS_NAMES_STRIDE = 13
GTRAINER_CLASS_NAMES_N = 107
# Item names live INSIDE the gItems struct (44-byte stride, name at offset 0,
# 14 bytes / 7 syllables max).
GITEM_NAMES_N = 375
GITEM_NAMES_LEN = 14


def decode_codepoints(rom: bytes, off: int, max_bytes: int, inv: dict) -> tuple[str, int, int]:
    """Decode a stride-bounded name into (text, hangul_count, unknown_count)."""
    out: list[str] = []
    n_hangul = 0
    n_unknown = 0
    for i in range(off, off + max_bytes, 2):
        if i + 2 > len(rom): break
        cp = struct.unpack_from(">H", rom, i)[0]
        if cp == 0xFF00 or cp == 0xFFFF or cp == 0x0000: break
        if 0x3700 <= cp <= 0x40FF:
            ch = inv.get(cp)
            if ch:
                out.append(ch)
                if "가" <= ch <= "힣": n_hangul += 1
            else:
                out.append(f"[{cp:04X}]")
                n_unknown += 1
        elif cp < 0x100:
            out.append("·")
        # else: skip
    return "".join(out), n_hangul, n_unknown


def main():
    rom = ROM_PATH.read_bytes()
    cm = json.loads(CODEPOINT_MAP.read_text())
    inv = {int(k, 16): v for k, v in cm.items()}
    corpus = json.loads(CORPUS.read_text())
    existing_offs = {r["offset"] for r in corpus["records"]}

    # Find next free record id
    max_id = max(r["id"] for r in corpus["records"])
    next_id = max_id + 1

    new_records: list[dict] = []

    def add_table_entries(base: int, stride: int, n: int, source_label: str):
        nonlocal next_id
        added = 0
        for i in range(n):
            off = base + i * stride
            # Skip if already in corpus
            if off in existing_offs: continue
            text, n_h, n_u = decode_codepoints(rom, off, stride, inv)
            if n_h < 1: continue  # skip empty/non-Korean entries
            new_records.append({
                "id": next_id,
                "offset": off,
                "text": text,
                "unknown": n_u,
                "hangul": n_h,
                "source": f"{source_label}[{i}]",
            })
            next_id += 1
            added += 1
        return added

    n_moves = add_table_entries(GMOVE_NAMES, GMOVE_NAMES_STRIDE,
                                GMOVE_NAMES_N, "gMoveNames")
    n_abil = add_table_entries(GABILITY_NAMES, GABILITY_NAMES_STRIDE,
                               GABILITY_NAMES_N, "gAbilityNames")
    n_spec = add_table_entries(GSPECIES_NAMES, GSPECIES_NAMES_STRIDE,
                               GSPECIES_NAMES_N, "gSpeciesNames")
    n_tc = add_table_entries(GTRAINER_CLASS_NAMES, GTRAINER_CLASS_NAMES_STRIDE,
                             GTRAINER_CLASS_NAMES_N, "gTrainerClassNames")
    # Item names: embedded inside gItems struct (44-byte stride, name at +0,
    # length 14). Each entry's name lives at GITEMS + i*44 + GITEM_NAMES_OFF.
    n_items = 0
    for i in range(GITEM_NAMES_N):
        off = GITEMS + i * GITEMS_STRIDE + GITEMS_NAME_OFF
        if off in existing_offs: continue
        text, n_h, n_u = decode_codepoints(rom, off, GITEM_NAMES_LEN, inv)
        if n_h < 1: continue
        new_records.append({
            "id": next_id,
            "offset": off,
            "text": text,
            "unknown": n_u,
            "hangul": n_h,
            "source": f"gItems[{i}].name",
        })
        next_id += 1
        n_items += 1

    corpus["records"].extend(new_records)
    notes = corpus.get("note")
    extend_note = (
        f"Extended with name-table entries (2026-05-12): "
        f"+{n_moves} moves, +{n_abil} abilities, +{n_spec} species, "
        f"+{n_tc} trainer classes, +{n_items} item names "
        f"({len(new_records)} total)."
    )
    if isinstance(notes, str):
        corpus["note"] = notes + " " + extend_note
    else:
        corpus["note"] = extend_note
    CORPUS.write_text(json.dumps(corpus, ensure_ascii=False, indent=1))
    print(f"corpus.ko.json: +{n_moves} moves, +{n_abil} abilities, "
          f"+{n_spec} species, +{n_tc} trainer classes, +{n_items} item names "
          f"({len(new_records)} new records, total {len(corpus['records'])})")


if __name__ == "__main__":
    main()
