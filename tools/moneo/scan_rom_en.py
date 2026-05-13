#!/usr/bin/env python3
"""Scan the canonical English LeafGreen ROM for dialog/text records.

Single-byte counterpart to scan_rom_2024.py (which walks the 2024 Korean
patch's 16-bit BE codepoints). Reuses the same pointer-target → message
walking strategy: find every u32 LE that looks like a ROM pointer, decode
the target as a Gen 3 EN charset stream terminated by 0xFF, validate by
printable-letter density.

Output: tools/moneo/corpus.en.json
        .moneo-artifacts/rom-text-en-raw.json
"""
from __future__ import annotations
import argparse
import json
import struct
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))
from rom_config_en import (  # noqa: E402
    ROM_PATH_EN, GBA_BASE,
    EN_CHARMAP, EN_END_MARKER, EN_NEWLINE_BYTES, EN_INLINE_PREFIXES_WITH_ARG,
)

ROOT = THIS_DIR.parents[1]
OUT_RAW = ROOT / ".moneo-artifacts/rom-text-en-raw.json"
OUT_CORPUS = THIS_DIR / "corpus.en.json"

# === Tuning (mirrors the KR scanner thresholds but expressed in *bytes* not codepoints) ===
MAX_RUN_BYTES = 800
MIN_RUN_BYTES = 4
MIN_KNOWN_LETTERS = 3
MIN_LETTER_DENSITY = 0.6


def is_letter(ch: str) -> bool:
    return ch.isalpha()


def read_message(rom: bytes, off: int, hard_end: int | None = None):
    """Decode a Gen 3 EN-charset string starting at `off`. Returns a
    dict with text + stats, or None if `off` doesn't open a clean message.
    """
    if off + 2 > len(rom):
        return None
    out: list[str] = []
    n_bytes = 0
    n_known_letters = 0
    n_unknown = 0
    max_consec_letters = 0
    cur_consec_letters = 0
    consec_other = 0
    i = off
    end_off = None
    limit = len(rom) if hard_end is None else min(len(rom), hard_end)
    while i < limit and n_bytes < MAX_RUN_BYTES:
        b = rom[i]
        if b == EN_END_MARKER:
            end_off = i
            break
        if b in EN_NEWLINE_BYTES:
            out.append("\n")
            i += 1
            n_bytes += 1
            cur_consec_letters = 0
            consec_other = 0
            continue
        if b in EN_INLINE_PREFIXES_WITH_ARG:
            if i + 1 >= limit:
                return None
            arg = rom[i + 1]
            if b == 0xFD:
                out.append(f"{{var:{arg:02X}}}")
            else:
                pass  # 0xFC = format/colour, silent
            i += 2
            n_bytes += 2
            cur_consec_letters = 0
            consec_other = 0
            continue
        ch = EN_CHARMAP.get(b)
        if ch is None:
            # Non-charmap byte: tolerate a few in a row (could be padding
            # at table seams), but bail when it's clearly bytecode.
            out.append("·")
            n_unknown += 1
            consec_other += 1
            cur_consec_letters = 0
            if consec_other >= 4:
                return None
        else:
            out.append(ch)
            consec_other = 0
            if is_letter(ch):
                n_known_letters += 1
                cur_consec_letters += 1
                max_consec_letters = max(max_consec_letters, cur_consec_letters)
            else:
                cur_consec_letters = 0
        i += 1
        n_bytes += 1

    if end_off is None:
        if hard_end is not None and i >= limit:
            end_off = i
        else:
            return None
    if n_bytes < MIN_RUN_BYTES:
        return None
    if n_known_letters < MIN_KNOWN_LETTERS:
        return None
    if max_consec_letters < MIN_KNOWN_LETTERS:
        return None
    text_bytes = n_known_letters + n_unknown
    density = n_known_letters / max(text_bytes, 1)
    if density < MIN_LETTER_DENSITY:
        return None
    return {
        "off": off,
        "end_off": end_off,
        "text": "".join(out),
        "n_bytes": n_bytes,
        "letters": n_known_letters,
        "unknown": n_unknown,
    }


def find_pointer_targets(rom: bytes) -> set[int]:
    targets: set[int] = set()
    rom_len = len(rom)
    for off in range(0, rom_len - 4):
        v = struct.unpack_from("<I", rom, off)[0]
        if (v & 0xFE000000) == GBA_BASE:
            target = v - GBA_BASE
            if 0xC0 < target < rom_len:
                targets.add(target)
    return targets


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    rom = ROM_PATH_EN.read_bytes()
    print(f"ROM: {ROM_PATH_EN}  ({len(rom):,} bytes)")

    print("\n[1/2] scanning for pointer literals…")
    targets = sorted(find_pointer_targets(rom))
    print(f"   pointer targets: {len(targets):,}")

    print("\n[2/2] decoding each target…")
    records: list[dict] = []
    seen: set[int] = set()
    for idx, off in enumerate(targets):
        if off in seen:
            continue
        next_off = targets[idx + 1] if idx + 1 < len(targets) else len(rom)
        hard_end = min(next_off, off + MAX_RUN_BYTES)
        msg = read_message(rom, off, hard_end=hard_end)
        if msg is None:
            continue
        records.append(msg)
        seen.add(off)
    print(f"   accepted {len(records):,} messages")

    print("\nSample (first 8 with letters>=10):")
    shown = 0
    for r in records:
        if r["letters"] >= 10:
            text = r["text"].replace("\n", " | ")
            print(f"   0x{r['off']:06X}  {text[:100]}")
            shown += 1
            if shown >= 8:
                break

    if args.dry:
        print("\n--dry: skipping writes")
        return 0

    OUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    raw = []
    for i, r in enumerate(records):
        end = r["end_off"]
        raw.append({
            "id": i,
            "offset": r["off"],
            "len": end - r["off"] + 1,
            "hex": rom[r["off"]:end + 1].hex(),
        })
    OUT_RAW.write_text(json.dumps({
        "rom": ROM_PATH_EN.name,
        "encoding": "gen3-en-singlebyte",
        "stats": {"records": len(raw), "rom_bytes": len(rom)},
        "records": raw,
    }, ensure_ascii=False, indent=1))
    print(f"\nwrote {OUT_RAW}")

    corpus = [{
        "id": i, "offset": r["off"], "text": r["text"],
        "letters": r["letters"], "unknown": r["unknown"],
    } for i, r in enumerate(records)]
    OUT_CORPUS.write_text(json.dumps({
        "version": 1,
        "rom": ROM_PATH_EN.name,
        "encoding": "gen3-en-singlebyte",
        "records": corpus,
        "stats": {
            "record_count": len(corpus),
            "letter_chars": sum(r["letters"] for r in records),
        },
    }, ensure_ascii=False, indent=1))
    print(f"wrote {OUT_CORPUS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
