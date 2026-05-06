#!/usr/bin/env python3
"""Static map -> text walker.

For each map in gMapGroups, collect the script seed pointers (object
events, coord triggers, sign events, mapScripts), scan each script's
bytecode window for u32 LE ROM pointers, and report which text records
are reachable. The resulting `mapsec -> set[rec_id]` mapping enables
"first encountered in <map>" attribution for cards in the deck.

Why pointer-scan a window instead of properly disassembling bytecode?
Because (a) most text references in scripts are loaded via the standard
`loadword 0, <ptr>` pattern (opcode 0x16, then dest, then 4-byte ptr) and
(b) we can match pointers loosely against the corpus -- random ROM bytes
that happen to look like a pointer to a non-text address won't resolve
to a corpus rec_id. False positives remain low because (corpus offset
set) is sparse compared to the full ROM.

Scripts can call other scripts via CALL (0x04) and GOTO (0x05). We
recursively follow those calls within a depth limit to cover branches.

Output: tools/moneo/map_text_index.json
"""
from __future__ import annotations
import argparse
import json
import struct
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
ROM = ROOT / "Pocket Monsters - LeafGreen (Korean).gba"
CORPUS_STATIC = ROOT / "app/src/main/assets/moneo/corpus.ko.json"
CORPUS_LIVE = ROOT / "tools/moneo/corpus.ko.live.json"
OUT = ROOT / "tools/moneo/map_text_index.json"

GBA_BASE = 0x08000000
GROUP_OFFSETS = [0x316294, 0x316384, 0x31648C, 0x31649C, 0x3164B4, 0x3164D4,
                 0x316294 + 146 * 4]


def u32(rom: bytes, off: int) -> int:
    return struct.unpack_from("<I", rom, off)[0]


def u16(rom: bytes, off: int) -> int:
    return struct.unpack_from("<H", rom, off)[0]


def is_rom_ptr(p: int, rom_len: int) -> bool:
    return GBA_BASE <= p < GBA_BASE + rom_len


def walk_maps(rom: bytes):
    """Yield (group, mapNum, header_off, mapsec, music) for each map."""
    n_groups = len(GROUP_OFFSETS) - 1
    for g in range(n_groups):
        start, end = GROUP_OFFSETS[g], GROUP_OFFSETS[g + 1]
        for i in range((end - start) // 4):
            p = u32(rom, start + i * 4)
            if not is_rom_ptr(p, len(rom)):
                continue
            mh = p - GBA_BASE
            mapsec = rom[mh + 20]
            music = u16(rom, mh + 16)
            yield g, i, mh, mapsec, music


def collect_seed_scripts(rom: bytes, header_off: int) -> list[int]:
    """Return ROM offsets of every seed script for this map."""
    seeds: list[int] = []
    rom_len = len(rom)

    # MapHeader layout:
    #   0x00 mapData ptr, 0x04 events ptr, 0x08 mapScripts ptr,
    #   0x0C connections ptr, 0x10 music, 0x12 layoutId, 0x14 mapsec, ...
    events_ptr = u32(rom, header_off + 4)
    map_scripts_ptr = u32(rom, header_off + 8)

    # mapScripts: list of {u8 type; u32 ptr} or {u8 type; u32 condPtr}; varies.
    # Type 0 terminates. We follow type-2/4-style entries that have a script ptr.
    if is_rom_ptr(map_scripts_ptr, rom_len):
        ms = map_scripts_ptr - GBA_BASE
        # Bound walk to avoid run-aways
        for _ in range(32):
            if ms + 1 > rom_len:
                break
            t = rom[ms]
            if t == 0:
                break
            # Standard pokeruby map-script types: 1=onMapLoadIfNotEnabled,
            # 2=onLoadFlag, 3=onTransitionFlag, 4=onWarpInto, 5=onMapLoad,
            # 6=onTransition, 7=onMapLoadIfTrue. Most have ptr at offset 1
            # (4 bytes); type 2/4 have a struct ptr at offset 1 instead. To
            # keep this simple, we just scan ROM at ms+1 and ms+5 for
            # ROM-ptrs; the false-positive rate is low (we only match against
            # the corpus offset set later anyway).
            for delta in (1, 5):
                if ms + delta + 4 <= rom_len:
                    p = u32(rom, ms + delta)
                    if is_rom_ptr(p, rom_len):
                        seeds.append(p - GBA_BASE)
            ms += 5

    # Events block:
    #   0x00 u8 nObjects, 0x01 u8 nWarps, 0x02 u8 nCoordScripts, 0x03 u8 nSigns
    #   0x04 u32 *objectEvents (24 bytes ea, script at +16)
    #   0x08 u32 *warps (8 bytes ea, no scripts)
    #   0x0C u32 *coordScripts (16 bytes ea, script at +12)
    #   0x10 u32 *bgEvents (12 bytes ea, script at +8 if kind 0 or 1)
    if is_rom_ptr(events_ptr, rom_len):
        evt = events_ptr - GBA_BASE
        if evt + 20 <= rom_len:
            n_obj = rom[evt + 0]
            n_coord = rom[evt + 2]
            n_sign = rom[evt + 3]
            obj_ptr = u32(rom, evt + 4)
            cs_ptr = u32(rom, evt + 12)
            sg_ptr = u32(rom, evt + 16)

            if is_rom_ptr(obj_ptr, rom_len) and n_obj > 0:
                base = obj_ptr - GBA_BASE
                for j in range(min(n_obj, 64)):
                    rec = base + j * 24
                    if rec + 20 > rom_len:
                        break
                    p = u32(rom, rec + 16)
                    if is_rom_ptr(p, rom_len):
                        seeds.append(p - GBA_BASE)

            if is_rom_ptr(cs_ptr, rom_len) and n_coord > 0:
                base = cs_ptr - GBA_BASE
                for j in range(min(n_coord, 64)):
                    rec = base + j * 16
                    if rec + 16 > rom_len:
                        break
                    p = u32(rom, rec + 12)
                    if is_rom_ptr(p, rom_len):
                        seeds.append(p - GBA_BASE)

            if is_rom_ptr(sg_ptr, rom_len) and n_sign > 0:
                base = sg_ptr - GBA_BASE
                for j in range(min(n_sign, 64)):
                    rec = base + j * 12
                    if rec + 12 > rom_len:
                        break
                    kind = rom[rec + 5]
                    if kind in (0, 1):  # script-bearing sign types
                        p = u32(rom, rec + 8)
                        if is_rom_ptr(p, rom_len):
                            seeds.append(p - GBA_BASE)

    return seeds


def collect_text_refs(rom: bytes, script_off: int, corpus_offsets: set,
                      visited: set | None = None,
                      depth: int = 0, max_depth: int = 3,
                      max_window: int = 512) -> set:
    """Find every u32 LE ROM-pointer in the [script_off, script_off+max_window]
    window that targets a known corpus offset.

    We deliberately do NOT try to walk bytecode opcode-by-opcode -- the
    pokefirered/pokeruby opcode set has many table-driven variants whose
    lengths I don't have a reference table for, so misalignment is the
    norm. Instead, we exploit the fact that real text references are
    encoded as `0x16 <reg> <ptr:4>` somewhere in the script, which means
    the 4-byte ptr is byte-aligned to the script's start (or off by 1-3
    depending on prior opcodes). Scanning all u32 alignments and
    membership-filtering against the corpus offset set picks up all real
    text references with low false-positive rate (random ROM bytes
    rarely produce a u32 that points at a corpus offset).

    To handle scripts that CALL/GOTO into other scripts, we also follow
    pointers that target ANOTHER script (i.e. a u32 that points at a
    location bytes-near a known seed). For simplicity we treat any
    pointer to ROM as a possible script jump and recurse with depth-
    limit; pointers that don't actually start a script are bounded
    (their windows yield nothing extra).
    """
    if visited is None:
        visited = set()
    if script_off in visited or depth > max_depth:
        return set()
    visited.add(script_off)
    rom_len = len(rom)

    found: set = set()
    sub_targets: set = set()
    end = min(script_off + max_window, rom_len)
    # Pass 1: every u32-aligned-or-misaligned pointer literal that hits a
    # known corpus offset. This is the main signal -- text references are
    # encoded as `0x16 <reg> <ptr:4>` somewhere in the script body, and a
    # corpus-membership filter discriminates real refs from coincidence.
    for i in range(script_off, end - 3):
        v = struct.unpack_from("<I", rom, i)[0]
        if (v & 0xFE000000) != GBA_BASE:
            continue
        t = v - GBA_BASE
        if t in corpus_offsets:
            found.add(t)

    # Pass 2: follow explicit CALL (0x04) and GOTO (0x05) opcodes. This is
    # narrower than chasing every u32 pointer (which over-recurses into
    # data tables) but recovers script-CALL chains that live above the
    # initial 512-byte window. We require the byte BEFORE the pointer to
    # be exactly 0x04 or 0x05, with the pointer immediately following --
    # the pokefirered/pokeruby canonical encoding. False positives are
    # bounded because the target must (a) look like a ROM pointer, (b)
    # land in the code half of ROM, and (c) when recursed-into, only
    # contributes refs that themselves hit corpus offsets.
    if depth < max_depth:
        for i in range(script_off, end - 4):
            op = rom[i]
            if op not in (0x04, 0x05):
                continue
            v = struct.unpack_from("<I", rom, i + 1)[0]
            if (v & 0xFE000000) != GBA_BASE:
                continue
            t = v - GBA_BASE
            # Skip if it points back into known text region (irrelevant
            # for control flow) or outside the code half of ROM.
            if t in corpus_offsets:
                continue
            if 0x100000 <= t < 0xC00000:
                sub_targets.add(t)

    for sub in sub_targets:
        found |= collect_text_refs(rom, sub, corpus_offsets, visited,
                                   depth + 1, max_depth, max_window)
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--summary", action="store_true",
                    help="print per-mapsec summary instead of writing JSON")
    args = ap.parse_args()

    rom = ROM.read_bytes()

    static = json.loads(CORPUS_STATIC.read_text())
    live = json.loads(CORPUS_LIVE.read_text())

    rec_by_offset: dict[int, dict] = {}
    for r in static["records"]:
        if r.get("offset") is not None:
            rec_by_offset[r["offset"]] = {**r, "region": "static"}
    for r in live["records"]:
        if r.get("offset") is not None:
            rec_by_offset[r["offset"]] = {**r, "region": "live"}

    corpus_offsets = set(rec_by_offset.keys())
    print(f"corpus offsets known: {len(corpus_offsets):,} "
          f"(static={len(static['records'])}, live={len(live['records'])})")

    mapsec_to_recids: dict[int, set[int]] = defaultdict(set)
    map_records: list[dict] = []
    n_seeds_total = 0
    n_text_refs = 0

    for g, m, mh, mapsec, music in walk_maps(rom):
        seeds = collect_seed_scripts(rom, mh)
        n_seeds_total += len(seeds)
        text_offs: set[int] = set()
        for s in seeds:
            text_offs |= collect_text_refs(rom, s, corpus_offsets)
        n_text_refs += len(text_offs)
        rec_ids = {rec_by_offset[o]["id"] for o in text_offs}
        mapsec_to_recids[mapsec] |= rec_ids
        map_records.append({
            "group": g, "mapNum": m, "mapsec": mapsec,
            "header": mh, "music": music,
            "seedScripts": len(seeds),
            "textRefs": sorted(text_offs),
            "recIds": sorted(rec_ids),
        })

    print(f"\nMaps walked: {len(map_records)}")
    print(f"Total seed scripts: {n_seeds_total}")
    print(f"Total text refs (sum across maps): {n_text_refs}")
    print(f"Distinct mapsec values that produced text refs: "
          f"{sum(1 for s in mapsec_to_recids.values() if s)}")

    # Top-talkers — mapsec values with the most distinct rec_ids
    print("\nTop 15 mapsec by rec_id count:")
    for ms, recs in sorted(mapsec_to_recids.items(), key=lambda kv: -len(kv[1]))[:15]:
        # peek at one rec to see what kind of text
        sample_id = next(iter(recs)) if recs else None
        if sample_id is not None:
            sample_rec = next((r for r in static["records"] + live["records"]
                               if r["id"] == sample_id), None)
            sample = (sample_rec["text"][:50] + "...") if sample_rec else ""
        else:
            sample = ""
        print(f"  mapsec 0x{ms:02X}: {len(recs):4d} rec_ids   sample: {sample!r}")

    if args.summary:
        return 0

    out = {
        "version": 1,
        "rom": ROM.name,
        "corpus_static": str(CORPUS_STATIC.relative_to(ROOT)),
        "corpus_live": str(CORPUS_LIVE.relative_to(ROOT)),
        "stats": {
            "maps": len(map_records),
            "seed_scripts_total": n_seeds_total,
            "text_refs_total_with_dupes": n_text_refs,
            "distinct_mapsecs_with_refs":
                sum(1 for s in mapsec_to_recids.values() if s),
        },
        "mapsec_to_rec_ids": {
            f"0x{ms:02X}": sorted(recs)
            for ms, recs in sorted(mapsec_to_recids.items())
        },
        "maps": map_records,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
