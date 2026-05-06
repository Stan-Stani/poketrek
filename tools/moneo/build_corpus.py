#!/usr/bin/env python3
"""Decode rom-text-ko-raw.json into corpus.ko.json using the (page, idx) -> Hangul
glyph map produced by build_glyph_map.py.

Encoding (per disassembly of text engine at ROM 0x384800):
  - byte <= 0xF0: single-byte char rendered with default page=0 (F0 base font).
    The byte itself is used as the idx into F0; F0 holds digits, ASCII letters,
    German umlauts, and the most common Korean syllables.
  - byte 0xF1..0xF6 + idx: Korean syllable from font page (page=byte-0xF0, idx)
  - byte 0xF7..0xF9: reserved/extended codes (treated as control)
  - byte 0xFA: scroll
  - byte 0xFB: clear
  - byte 0xFC + 1 byte: format code (consume 1 param byte)
  - byte 0xFD + 1 byte: var substitution (consume 1 param byte)
  - byte 0xFE: line-feed
  - byte 0xFF: end-of-record
"""
from __future__ import annotations
import json
from pathlib import Path
import sys

GLYPH_MAP = Path("tools/moneo/glyph-map.json")
RAW = Path(".moneo-artifacts/rom-text-ko-raw.json")
OUT = Path("app/src/main/assets/moneo/corpus.ko.json")


def decode_record(raw_bytes: list[int], glyph_map: dict[str, str]) -> str:
    out: list[str] = []
    i = 0
    n = len(raw_bytes)
    while i < n:
        b = raw_bytes[i]
        if b == 0xFF:
            break
        if b == 0xFE:
            out.append("\n"); i += 1; continue
        if b == 0xFA or b == 0xFB:
            # scroll/clear — represent as paragraph break
            out.append("\n\n"); i += 1; continue
        if b in (0xFC, 0xFD) and i + 1 < n:
            # consume one param byte; emit placeholder for substitution
            param = raw_bytes[i + 1]
            if b == 0xFD:
                out.append(f"{{var:{param:02X}}}")
            i += 2; continue
        if 0xF1 <= b <= 0xF6 and i + 1 < n:
            page = b - 0xF0
            idx = raw_bytes[i + 1]
            ch = glyph_map.get(f"F{page},{idx}")
            if ch is None:
                out.append(f"\u25A1")  # □ placeholder for unknown glyph
            else:
                out.append(ch)
            i += 2; continue
        if b in (0xF7, 0xF8, 0xF9) and i + 1 < n:
            # treat as 2-byte unknown control
            i += 2; continue
        # NOTE: 0xF0 itself is rejected by the prebyte handler (`bls .return`
        # at <=0xF0), so it falls through to the default page=0 path below.
        # Bytes <= 0xF0 default to page=0 in the engine (per disasm). The byte
        # itself is the idx into F0. F0 holds digits, ASCII letters, German
        # umlauts, and the most common Korean syllables.
        if b == 0x00:
            pass  # NUL/padding; ignore
        else:
            ch = glyph_map.get(f"F0,{b}")
            if ch is not None:
                out.append(ch)
            elif 0x20 <= b <= 0x7E:
                out.append(chr(b))  # fallback for unmapped printable ASCII
            else:
                out.append("·")  # · unmapped non-printable
        i += 1
    return "".join(out)


def main() -> int:
    glyph_data = json.loads(GLYPH_MAP.read_text(encoding="utf-8"))
    glyph_map: dict[str, str] = glyph_data["map"]
    print(f"Loaded glyph map: {len(glyph_map)} entries")

    raw_data = json.loads(RAW.read_text(encoding="utf-8"))
    records = raw_data["records"]
    print(f"Loaded {len(records)} raw records")

    out_records = []
    total_unknown = 0
    total_chars = 0
    for i, rec in enumerate(records):
        hex_str = rec.get("hex", "")
        if not hex_str:
            continue
        bytes_list = [int(hex_str[j:j+2], 16) for j in range(0, len(hex_str), 2)]
        decoded = decode_record(bytes_list, glyph_map)
        unk = decoded.count("\u25A1")
        total_unknown += unk
        total_chars += len(decoded)
        # Heuristic: only keep records that look like dialog (have at least one
        # Korean Hangul char and aren't dominated by unknown glyphs)
        hangul_count = sum(1 for c in decoded if "\uAC00" <= c <= "\uD7A3")
        if hangul_count == 0:
            continue
        out_records.append({
            "id": i,
            "offset": rec.get("offset"),
            "text": decoded,
            "unknown": unk,
            "hangul": hangul_count,
        })

    coverage = 1.0 - (total_unknown / max(total_chars, 1))
    print(f"Decoded {len(out_records)} records, total chars={total_chars}, "
          f"unknown={total_unknown} (coverage={coverage:.1%})")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "version": 1,
        "rom": "Pocket Monsters - LeafGreen (Korean).gba",
        "records": out_records,
        "stats": {
            "record_count": len(out_records),
            "total_chars": total_chars,
            "unknown_glyphs": total_unknown,
            "coverage": round(coverage, 4),
            "map_size": len(glyph_map),
        }
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wrote {OUT}")

    # Spot-check first 5 non-trivial records
    print("\n--- spot-check ---")
    shown = 0
    for r in out_records:
        text = r["text"].replace("\n", " | ")
        if len(text) > 6 and r["unknown"] < len(text) // 2:
            print(f"  [{r['id']}] {text[:80]}")
            shown += 1
            if shown >= 8:
                break
    return 0


if __name__ == "__main__":
    sys.exit(main())
