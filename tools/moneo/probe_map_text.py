#!/usr/bin/env python3
"""Korean LeafGreen map → text reverse-engineering probe.

This is a partial-progress investigative tool, not a finished pipeline. It
captures the state of the (rec_id → area_id) mapping work as of session
2026-05-06 so a future session can resume without re-discovering the layout.

WHAT'S WORKING
==============

1. Map structure decoded:
   * gMapGroups[6] at ROM offset 0x316740 (six u32 ptrs, one per group).
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
   produces readable Korean (e.g. "좋아!나가볼까?").

WHAT'S BLOCKED
==============

A. The rendered text does NOT appear verbatim in `corpus.ko.json`, even
   after stripping `{var:XX}` substitutions and normalizing whitespace.
   Hypotheses (none confirmed):
   * The runtime synthesizes display strings from multiple corpus records
     plus name substitutions, so no single record matches.
   * `corpus.ko.json` was built from a different ROM region than the one
     the live engine actually pulls from — there may be a parallel "live"
     region or a cache that's populated on-the-fly.
   * The runtime translation hook keeps the rendered bytes in EWRAM only;
     they were never extracted into corpus.ko.json.

B. `gMapHeader` (the active-map copy) was not found by signature search in
   either IWRAM or EWRAM. Diffing IWRAM/EWRAM between savestates at
   nominally-different maps yielded zero matching candidates. Possible
   reasons: the savestates may both be on the same map (or no map yet —
   intro sequence), or `gMapHeader` is stored in a non-standard format.
   Without it we can't tag a captured text rendering with its current map.

C. NPC scripts in ROM still reference the OLD (pre-translation, kana-rendered
   Japanese) text region at 0x180000-0x350000. There are 15,635 such
   references across 98 maps. The fan-translation hook that maps these to
   Korean (corpus.ko.json's region 0x35D000+) is not a static lookup table:
   * No (old, new) ptr pair arrays found.
   * No flat new-ptr arrays at ROM ranges where scripts reference them.
   * The corpus rec_offsets are not referenced as u32 literals anywhere in ROM.

NEXT STEPS (for a future session)
=================================

1. Find `gMapHeader` by RUNTIME tracing instead of signature search:
   * Set a breakpoint at the function that reads gMapHeader.events when
     transitioning maps. Capture the EWRAM/IWRAM read address.
   * Or: instrument mgba_capture to dump RAM each frame after a known
     map-transition input sequence, then diff.

2. Find the runtime text-translation hook:
   * Set a memory-read watchpoint on a high-frequency corpus rec offset
     (e.g. rec0 at 0x35D800 — but it's "garbled" so may never be read).
     Use a Pokédex-entry record like rec4347 instead.
   * Or: breakpoint at higher levels in the text engine — one level above
     0x080062B4 (per-glyph render) — to see what loads bytes into the
     EWRAM buffer at strptr.

3. Once gMapHeader is reachable, capture (rendered_korean_text, mapsec)
   pairs across many savestates / playthrough segments. Match the rendered
   text fuzzy-against corpus.ko.json (or against the new "live" region if
   discovered) → rec_ids. Build mapsec → list[rec_id]. Manually annotate
   each mapsec with its area_id (areas.json).

USAGE
=====

  # Print the map table summary (no emulator needed).
  python3 tools/moneo/probe_map_text.py --summary

  # Capture EWRAM + tokens from a savestate, decode the rendered Korean.
  python3 tools/moneo/probe_map_text.py --state koreanStartSaveState.ss0
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
