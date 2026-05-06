#!/usr/bin/env python3
"""Korean LeafGreen map -> text reverse-engineering probe.

Captures the state of (rec_id -> area_id) mapping recon. Updated 2026-05-06
after the prior blocker was resolved by `find_text_in_rom.py` (see below).

KEY FINDING (resolves the prior "runtime synthesis" blocker)
============================================================

The rendered Korean text from EWRAM exists VERBATIM in ROM. The previous
session's hypothesis -- that the engine synthesizes display strings via a
runtime translation hook -- is WRONG. Verified: the rendered string from
`koreanStartSaveState.ss0` ("쿤는...하고있다!...좋아!나가볼까?") sits at
ROM 0x17BF36 (terminator FF at 0x17BF59). The leading "쿤" was not a
different character -- it's `FD 01` (player-name var) that the engine
substitutes at render time.

What was previously called the "OLD pre-translation Japanese region"
(0x069000..0x350000) actually contains the LIVE Korean dialog. The fan
translation patched the existing Japanese region in-place rather than
relocating. NPC scripts still point at those original addresses; those
addresses now hold Korean. Specifically (from `find_text_in_rom.py`):

  * 48,584 candidate-valid Korean messages in ROM[:0x800000]
  * 341 dense clusters (>=30 messages each) total 31,448 messages
  * 6,630 u32 ROM-pointer literals in ROM[:0xC00000] hit a message start:
      - 4,147 into the "live" region (0x069000..0x350000)
      -   175 into the cluster containing our verified rendered text
      - exactly 1 pointer (ROM[0x17BEE3]) targets 0x17BF36 directly

corpus.ko.json (records starting at 0x35D7FA / "힌힌{VDD}...") was built
from leftover untranslated data, not the live region. That is why none of
its records matched the rendered text.

WHAT'S WORKING
==============

1. Map structure decoded:
   * gMapGroups[6] at ROM offset 0x316740, walked all 146 maps' events.
   * 146 maps total: 60 + 66 + 4 + 6 + 8 + 2 across groups 0-5.
   * Group-array offsets: [0x316294, 0x316384, 0x31648C, 0x31649C, 0x3164B4,
     0x3164D4]; the 7th value (0x316294 + 146*4) terminates group 5.
   * MapHeader is the standard 28-byte FRLG layout: 4 ROM ptrs (mapData,
     events, mapScripts, connections), then u16 music, u16 layoutId, u8
     mapsec, u8 cave, u8 weather, u8 mapType, u16 _, u8 escapeRope, u8 flags,
     u8 battleType, u8 _.
   * MapEvents is also standard: 4 u8 counts (obj, warp, scr, sign) + 4 u32
     ptrs. ObjectEvent is 24 bytes; CoordScript is 16; SignEvent is 12.

2. mGBA-driven text capture pipeline works headlessly via
   `tools/moneo/mgba_capture/build/mgba_capture` (built from capture.c).
   Per glyph render, captures `(frame, page, idx, mailbox, strptr)`.
   `--dump-ewram-dir` periodically saves EWRAM (the strptrs are EWRAM
   offsets, 0x02xxxxxx, into the in-flight dialog buffer).

3. Decoding `ewram[strptr - 0x02000000:]` with `tools/moneo/glyph-map.json`
   produces readable Korean.

4. `find_text_in_rom.py` reverse-encodes a Korean string into glyph bytes
   and locates it in ROM. Use it to verify any captured rendered text
   against the live ROM region.

NEXT STEPS -- area attribution is now a STATIC problem
======================================================

No runtime hook needed. Map -> text resolution becomes:

1. Re-extract corpus from the live region (0x069000..0x6D0000):
   * Walk every 0xFF terminator; treat each subsequent run of glyph bytes
     as a record (filter by hangul count + zero invalid bytes -- see the
     msg_quality function inside find_text_in_rom.py / cluster scan).
   * Output schema: same as current corpus.ko.json plus a `region` field
     so callers can distinguish live vs leftover records.

2. Static map -> text mapping:
   * For each MapHeader, follow events.scripts and mapScripts.
   * For each script blob, scan u32 LE literals; ones that hit a known
     message start are dialog references.
   * Build mapsec -> set[rec_offset] -> set[rec_id].

3. (Optional) Disassemble the script bytecode to filter spurious pointer
   matches. The likely text-loading opcodes are `loadword R0, <ptr>`
   followed by `callstd <type>` -- but a u32-literal scan should already
   give a clean signal because random data rarely coincides with a valid
   message-start offset.

4. Annotate areas.json with each mapsec's rec_id set; surface the first
   mapsec each rec_id appears in as that card's "first encountered in".

gMapHeader RAM-search is no longer on the critical path -- attribution
becomes static. Keep it as a fallback if a script's text references are
ambiguous.

USAGE
=====

  # Print the map table summary (no emulator needed).
  python3 tools/moneo/probe_map_text.py --summary

  # Capture EWRAM + tokens from a savestate, decode the rendered Korean.
  python3 tools/moneo/probe_map_text.py --state koreanStartSaveState.ss0

  # Verify a rendered string is in ROM and locate its offset:
  python3 tools/moneo/find_text_in_rom.py "<korean text>"
"""
from __future__ import annotations
import argparse
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROM = ROOT / "Pocket Monsters - LeafGreen (Korean).gba"
GLYPH_MAP = ROOT / "tools/moneo/glyph-map.json"
CAPTURE_BIN = ROOT / "tools/moneo/mgba_capture/build/mgba_capture"
CORPUS = ROOT / "app/src/main/assets/moneo/corpus.ko.json"

GROUPS_PTR_TABLE = 0x316740
GROUP_OFFSETS = [0x316294, 0x316384, 0x31648C, 0x31649C, 0x3164B4, 0x3164D4,
                 0x316294 + 146 * 4]


def u32(rom: bytes, off: int) -> int:
    return struct.unpack_from("<I", rom, off)[0]


def u16(rom: bytes, off: int) -> int:
    return struct.unpack_from("<H", rom, off)[0]


def is_rom_ptr(p: int, rom_len: int) -> bool:
    return 0x08000000 <= p < 0x08000000 + rom_len


def walk_maps(rom: bytes):
    """Yield (group, mapNum, header_offset, mapsec, music) for each map."""
    n_groups = len(GROUP_OFFSETS) - 1
    for g in range(n_groups):
        start, end = GROUP_OFFSETS[g], GROUP_OFFSETS[g + 1]
        for i in range((end - start) // 4):
            p = u32(rom, start + i * 4)
            if not is_rom_ptr(p, len(rom)):
                continue
            mh = p - 0x08000000
            mapsec = rom[mh + 20]
            music = u16(rom, mh + 16)
            yield g, i, mh, mapsec, music


def cmd_summary():
    rom = ROM.read_bytes()
    print(f"ROM: {ROM.name} ({len(rom):,} bytes)")
    print(f"gMapGroups @ 0x{GROUPS_PTR_TABLE:X}")
    counts: dict[int, int] = {}
    mapsec_counts: dict[int, int] = {}
    for g, m, mh, ms, mu in walk_maps(rom):
        counts[g] = counts.get(g, 0) + 1
        mapsec_counts[ms] = mapsec_counts.get(ms, 0) + 1
    for g in sorted(counts):
        print(f"  group {g}: {counts[g]} maps")
    print(f"\nDistinct mapsec values: {len(mapsec_counts)}")
    for ms in sorted(mapsec_counts):
        print(f"  mapsec 0x{ms:02X}: {mapsec_counts[ms]} maps")


def decode_text_at(buf: bytes, off: int, glyph_map: dict, max_len: int = 200) -> str:
    out: list[str] = []
    i = off
    end = min(off + max_len, len(buf))
    while i < end:
        b = buf[i]
        if b == 0xFF:
            break
        if b == 0xFE:
            out.append("\n"); i += 1; continue
        if b in (0xFA, 0xFB):
            i += 1; continue
        if b in (0xFC, 0xFD) and i + 1 < end:
            i += 2; continue
        if 0xF1 <= b <= 0xF6 and i + 1 < end:
            out.append(glyph_map.get(f"F{b - 0xF0},{buf[i+1]}", "?"))
            i += 2; continue
        out.append(glyph_map.get(f"F0,{b}", ""))
        i += 1
    return "".join(out)


def cmd_capture(args):
    if not CAPTURE_BIN.exists():
        sys.exit(f"Capture binary missing: {CAPTURE_BIN}\n"
                 f"Build via: cd tools/moneo/mgba_capture && cmake -B build && cmake --build build")
    state = Path(args.state)
    out_json = Path(args.out_dir) / "cap.json"
    ewram_dir = Path(args.out_dir) / "ewram"
    ewram_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(CAPTURE_BIN),
        "--rom", str(ROM),
        "--state", str(state),
        "--seconds", str(args.seconds),
        "--out", str(out_json),
        "--dump-ewram-dir", str(ewram_dir),
        "--dump-ewram-every", "30",
    ]
    print("$", " ".join(cmd))
    subprocess.check_call(cmd)
    cap = json.loads(out_json.read_text())
    ewrams = sorted(ewram_dir.glob("ewram-*.bin"))
    if not ewrams:
        print("No EWRAM snapshots; capture may have run without dialog rendering.")
        return
    ewram = ewrams[-1].read_bytes()
    glyph_map = json.loads(GLYPH_MAP.read_text())["map"]
    seen: set[str] = set()
    print(f"\n--- decoded text per token (capture had {len(cap['tokens'])} hits) ---")
    for t in cap["tokens"]:
        sp = t["strptr"]
        if not (0x02000000 <= sp < 0x02040000):
            continue
        text = decode_text_at(ewram, sp - 0x02000000, glyph_map)
        if text[:30] in seen:
            continue
        seen.add(text[:30])
        print(f"  frame={t['frame']} strptr=0x{sp:X} page={t['page']} idx={t['idx']}: {text!r}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--summary", action="store_true", help="print map table summary")
    p.add_argument("--state", help="savestate path (.ss0) for capture")
    p.add_argument("--seconds", type=int, default=4)
    p.add_argument("--out-dir", default="/tmp/probe_map_text")
    args = p.parse_args()
    if args.summary:
        cmd_summary()
        return 0
    if args.state:
        cmd_capture(args)
        return 0
    p.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
