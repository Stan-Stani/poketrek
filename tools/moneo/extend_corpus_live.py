#!/usr/bin/env python3
"""Extract the LIVE Korean dialog region into a separate corpus file.

The existing `app/src/main/assets/moneo/corpus.ko.json` (records 0..N) was
extracted from ROM 0x35D800..0x5C09C6, which holds static text (Pokédex
entries, item descriptions, menu strings, some cutscene strings). It is
shipped in the APK and used by deck-building tooling.

It does NOT contain the live NPC overworld dialog that the player reads
when talking to townspeople. That live dialog lives in ROM
0x069000..0x350000 — the region the fan translation patched in-place
over the original Japanese. NPC scripts reference these addresses
directly. See `find_text_in_rom.py` and `probe_map_text.py` for the
recon.

This tool writes the live-region records to a SEPARATE file
(`tools/moneo/corpus.ko.live.json`) — outside `app/src/main/assets/` so
the APK is not bloated by ~20K records of dialog text that the runtime
doesn't need. Tools that want the full corpus (e.g. the upcoming static
script→text walker) load both and join.

Output schema mirrors corpus.ko.json: {version, rom, records: [{id,
offset, text, unknown, hangul, region: "live"}]}. New record IDs start
at max(existing_id) + 1, so a tool that loads both files and indexes by
id will not collide.

Usage:
    python3 tools/moneo/extend_corpus_live.py        # write live file
    python3 tools/moneo/extend_corpus_live.py --dry  # report-only
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROM = ROOT / "Pocket Monsters - LeafGreen (Korean).gba"
GLYPH_MAP = ROOT / "tools/moneo/glyph-map.json"
CORPUS = ROOT / "app/src/main/assets/moneo/corpus.ko.json"
LIVE_CORPUS = ROOT / "tools/moneo/corpus.ko.live.json"


def is_hangul(ch: str) -> bool:
    return "가" <= ch <= "힣"


def msg_quality(rom: bytes, off: int, gm: dict, max_len: int = 250):
    """Walk a message starting at `off`. Return (length_chars, hangul, invalid, end_off)
    where end_off is the position of the 0xFF terminator (exclusive of FF itself).
    Return None if no terminator is found within max_len bytes."""
    i = off
    n = 0
    hangul = 0
    invalid = 0
    end = min(off + max_len, len(rom))
    while i < end:
        b = rom[i]
        if b == 0xFF:
            return (n, hangul, invalid, i)
        if b == 0xFE:
            i += 1
            continue
        if b in (0xFA, 0xFB):
            i += 1
            continue
        if b in (0xFC, 0xFD) and i + 1 < len(rom):
            i += 2
            n += 1
            continue
        if 0xF1 <= b <= 0xF6 and i + 1 < len(rom):
            ch = gm.get(f"F{b - 0xF0},{rom[i + 1]}")
            if ch is None:
                invalid += 1
            elif is_hangul(ch):
                hangul += 1
            i += 2
            n += 1
            continue
        ch = gm.get(f"F0,{b}")
        if ch is None:
            invalid += 1
        elif is_hangul(ch):
            hangul += 1
        i += 1
        n += 1
    return None


def decode(rom: bytes, off: int, gm: dict, max_len: int = 500) -> tuple[str, int, int]:
    """Decode a message at `off`. Returns (text, unknown_count, hangul_count).
    Stops at 0xFF (terminator) or end of buffer."""
    out: list[str] = []
    unknown = 0
    hangul = 0
    i = off
    end = min(off + max_len, len(rom))
    while i < end:
        b = rom[i]
        if b == 0xFF:
            break
        if b == 0xFE:
            out.append("\n"); i += 1; continue
        if b in (0xFA, 0xFB):
            out.append("\n\n"); i += 1; continue
        if b in (0xFC, 0xFD) and i + 1 < len(rom):
            param = rom[i + 1]
            if b == 0xFD:
                out.append(f"{{var:{param:02X}}}")
            i += 2; continue
        if 0xF1 <= b <= 0xF6 and i + 1 < len(rom):
            ch = gm.get(f"F{b - 0xF0},{rom[i + 1]}")
            if ch is None:
                out.append("□"); unknown += 1
            else:
                out.append(ch)
                if is_hangul(ch): hangul += 1
            i += 2; continue
        ch = gm.get(f"F0,{b}")
        if ch is None:
            out.append("□"); unknown += 1
        else:
            out.append(ch)
            if is_hangul(ch): hangul += 1
        i += 1
    return "".join(out), unknown, hangul


import struct


def find_message_starts(rom: bytes, gm: dict, scan_end: int):
    """Yield (start_off, end_off) for every valid Korean message that is
    the target of a u32 LE ROM-pointer literal somewhere in ROM.

    We use POINTER-TARGETS as the canonical message-start signal. Why not
    just walk 0xFF terminators? Because in the live dialog region
    (~0x069000..0x350000), text records sit immediately after script
    bytecode (no 0xFF separator), AND script bytecode bytes happen to
    decode to valid-looking glyphs. The FF-followed approach over-merges
    script bytecode into "messages" that start at the wrong offset.

    Pointer-targets are unambiguous: scripts only call into messages by
    storing a u32 ROM-pointer somewhere in ROM. If a u32 literal points
    at a location that decodes to valid Korean (hangul present, no
    invalid bytes, FF terminator within 500 bytes), that location is a
    real record start.
    """
    GBA_BASE = 0x08000000
    targets = set()
    # Scan ROM[:0xC00000] for u32 LE bytes that look like a ROM pointer.
    ptr_scan_end = min(0xC00000, len(rom) - 4)
    for off in range(0, ptr_scan_end):
        v = struct.unpack_from("<I", rom, off)[0]
        if (v & 0xFE000000) == GBA_BASE:
            target = v - GBA_BASE
            # Skip GBA cartridge header (0x00..0xC0) and very-low offsets
            # where short u32 literal collisions with "0x080000xx" produce
            # coincidental matches against random ROM bytes that decode to
            # tiny "messages" like "양야".
            if 0xC0 < target < scan_end:
                targets.add(target)

    # Validate each target via msg_quality and emit (start, end_off).
    spans: list[tuple[int, int]] = []
    for c in sorted(targets):
        q = msg_quality(rom, c, gm, max_len=500)
        if q is None:
            continue
        length, hangul, invalid, end = q
        if hangul >= 1 and invalid == 0 and length >= 2:
            spans.append((c, end))

    for start, end in spans:
        yield (start, end)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry", action="store_true",
                    help="Don't write; just report counts and a few samples.")
    ap.add_argument("--scan-end", type=lambda s: int(s, 0), default=0x800000,
                    help="Scan ROM[:scan_end] for messages (default 0x800000).")
    args = ap.parse_args()

    rom = ROM.read_bytes()
    gm = json.loads(GLYPH_MAP.read_text())["map"]
    corpus = json.loads(CORPUS.read_text())
    existing = {r["offset"]: r for r in corpus["records"] if r.get("offset") is not None}
    next_id = max((r["id"] for r in corpus["records"]), default=-1) + 1

    print(f"corpus.ko.json: {len(corpus['records']):,} records, max id = {next_id - 1}")
    print(f"existing offsets covered: {len(existing):,}")
    print(f"scanning ROM[0..0x{args.scan_end:X}] for new messages...")

    new_records = []
    skipped_dup = 0
    for start, end in find_message_starts(rom, gm, args.scan_end):
        if start in existing:
            skipped_dup += 1
            continue
        text, unk, han = decode(rom, start, gm)
        new_records.append({
            "id": next_id,
            "offset": start,
            "text": text,
            "unknown": unk,
            "hangul": han,
            "region": "live",
        })
        next_id += 1

    print(f"new records: {len(new_records):,}  (duplicates of existing offsets skipped: {skipped_dup:,})")
    if new_records:
        print("\nFirst 5 new records:")
        for r in new_records[:5]:
            print(f"  rec{r['id']} @ 0x{r['offset']:X}: {r['text'][:70]!r}")
        # Sanity check: does the rendered test message at 0x17BF36 land here?
        match = next((r for r in new_records if r["offset"] == 0x17BF36), None)
        if match:
            print(f"\nVerified rendered-text record: rec{match['id']} @ 0x17BF36: {match['text']!r}")
        else:
            print("\nWARNING: 0x17BF36 not in new records (expected from prior recon)")

    if args.dry:
        print("\n[--dry] Not writing.")
        return 0

    total_chars = sum(len(r["text"]) for r in new_records)
    unknown = sum(r["unknown"] for r in new_records)
    coverage = 1 - unknown / total_chars if total_chars else 0.0
    out = {
        "version": 1,
        "rom": corpus.get("rom", ROM.name),
        "note": ("Live-region records (NPC dialog, ROM 0x000000..0x800000 "
                 "minus static-corpus offsets). Pointer-target seeded; see "
                 "tools/moneo/extend_corpus_live.py."),
        "static_corpus_path": "app/src/main/assets/moneo/corpus.ko.json",
        "id_offset": next_id - len(new_records),
        "stats": {
            "record_count": len(new_records),
            "total_chars": total_chars,
            "unknown_glyphs": unknown,
            "coverage": round(coverage, 4),
        },
        "records": new_records,
    }
    LIVE_CORPUS.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(f"wrote {LIVE_CORPUS} ({len(new_records):,} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
