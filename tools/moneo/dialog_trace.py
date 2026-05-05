#!/usr/bin/env python3
"""Live trace of Korean LeafGreen text engine via mGBA GDB stub.

Usage:

  # 1. Launch mGBA with the GDB stub (separate terminal):
  mgba -g 'Pocket Monsters - LeafGreen (Korean).gba'

  # 2. Verify the GDB plumbing:
  python3 tools/moneo/dialog_trace.py selftest

  # 3. Capture a dialog session (user plays mGBA; ctrl-C to stop):
  python3 tools/moneo/dialog_trace.py capture --out .moneo-artifacts/trace.json

  # 4. Build (page,idx) -> fingerprint map from one-or-more capture files:
  python3 tools/moneo/dialog_trace.py build-map \
      --traces .moneo-artifacts/trace*.json \
      --out    .moneo-artifacts/runtime-charmap.json

The capture loop sets a hardware breakpoint at the per-glyph render entry
0x080062B4 (Thumb). Per capstone disassembly the function takes r0 packed:

    page = r0 & 0xF                 # 1..6 (Korean) or 7 (extended)
    idx  = (r0 >> 4) & 0xFFF        # 0..255 in practice (idx byte)

After every batch of N hits (or after a quiet timeout), it snapshots VRAM
charblock-0..3 (16 KB × 4 from 0x06000000) and SB31 (2 KB from 0x0600F800),
then emits a (page, idx, [fp_cb0..fp_cb3]) record.

NOTE: this script does NOT drive the emulator UI — the user (or an external
input-injection script) must play through dialog screens for tokens to flow.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gdb_client import GDBClient  # type: ignore

# ---- Engine addresses (from tools/moneo/disasm_engine.md) -------------------
ENGINE_ENTRY      = 0x08384800   # pre-byte handler
GLYPH_RENDER      = 0x080062B4   # per-syllable render function (Thumb)
PAGE_MAILBOX      = 0x03007E3F   # IWRAM byte: current page (1..6) or 0

VRAM_BASE         = 0x06000000
VRAM_BG_BYTES     = 65536
SB31_OFFSET       = 31 * 2048   # 0xF800
TILE_BYTES        = 32          # 4bpp 8x8
CHARBLOCK_SIZE    = 16384

TEXT_ROW_TOPS     = [3, 5, 7, 10, 12, 15, 17]
MAP_COLS          = 32
CHARS_PER_LINE    = 11

# ---- Helpers ----------------------------------------------------------------
def fingerprint_tile_group(vram64k: bytes, tl: int, tr: int, bl: int, br: int) -> str | None:
    """SHA-256[:8] of 4 tiles (TL,TR,BL,BR) at any of charblocks 0..3.
    Returns the FIRST charblock whose 128 bytes hash to a known-non-blank
    output. Caller filters; here we always return cb=0 hash."""
    if len(vram64k) < VRAM_BG_BYTES:
        return None
    raw = bytearray(128)
    cb_base = 0  # caller can vary cb if needed; for now use cb 0.
    for i, idx in enumerate((tl, tr, bl, br)):
        off = cb_base * CHARBLOCK_SIZE + idx * TILE_BYTES
        if off + TILE_BYTES > VRAM_BG_BYTES:
            raw[i*TILE_BYTES:(i+1)*TILE_BYTES] = b"\x00"*TILE_BYTES
        else:
            raw[i*TILE_BYTES:(i+1)*TILE_BYTES] = vram64k[off:off+TILE_BYTES]
    return hashlib.sha256(bytes(raw)).hexdigest()[:16]


def fingerprint_all_charblocks(vram64k: bytes, tl: int, tr: int, bl: int, br: int) -> list[str]:
    """Return fingerprints for all 4 charblocks. The Kotlin runtime tries
    each charblock until a known one matches; we capture all four so the
    offline matcher can pick the right one against ko_charmap.json."""
    fps = []
    for cb in range(4):
        raw = bytearray(128)
        for i, idx in enumerate((tl, tr, bl, br)):
            off = cb * CHARBLOCK_SIZE + idx * TILE_BYTES
            if off + TILE_BYTES > VRAM_BG_BYTES:
                raw[i*TILE_BYTES:(i+1)*TILE_BYTES] = b"\x00"*TILE_BYTES
            else:
                raw[i*TILE_BYTES:(i+1)*TILE_BYTES] = vram64k[off:off+TILE_BYTES]
        fps.append(hashlib.sha256(bytes(raw)).hexdigest()[:16])
    return fps


def sb31_tile(vram: bytes, row: int, col: int) -> int:
    off = SB31_OFFSET + (row * MAP_COLS + col) * 2
    if off + 2 > len(vram): return 0
    return (vram[off] | (vram[off+1] << 8)) & 0x3FF


def visible_tile_groups(vram: bytes) -> list[tuple[int, int, int, int, int, int]]:
    """Return list of (line, char_pos, tl, tr, bl, br) for every 2x2 tile group
    in the visible text rows that has any non-zero tile index."""
    out = []
    for line, top in enumerate(TEXT_ROW_TOPS):
        # find first non-zero col, then walk 11 chars
        start_col = None
        for col in range(MAP_COLS):
            if sb31_tile(vram, top, col) != 0:
                start_col = col; break
        if start_col is None: continue
        for n in range(CHARS_PER_LINE):
            col = start_col + n*2
            if col + 1 >= MAP_COLS: break
            tl = sb31_tile(vram, top,     col)
            tr = sb31_tile(vram, top,     col+1)
            bl = sb31_tile(vram, top+1,   col)
            br = sb31_tile(vram, top+1,   col+1)
            if tl == 0 and tr == 0 and bl == 0 and br == 0: continue
            out.append((line, n, tl, tr, bl, br))
    return out


# ---- Subcommands ------------------------------------------------------------
def cmd_selftest(args):
    c = GDBClient()
    c.connect()
    print("[ok] connected to mGBA gdb stub at", f"{c.host}:{c.port}")
    print("[ok] qSupported:", c.cmd("qSupported:")[:100])
    regs = c.read_regs()
    print(f"[ok] read {len(regs)} registers; pc={regs[15]:#010x} cpsr={regs[16]:#010x}")
    title = c.read_mem(0x080000A0, 12)
    print(f"[ok] ROM header @0x080000A0: {title!r}")
    page = c.read_mem(PAGE_MAILBOX, 1)
    print(f"[ok] page mailbox @{PAGE_MAILBOX:#x}: {page.hex()}")
    # Set + clear hwbreak
    c.set_hw_break(GLYPH_RENDER, kind=2)
    print(f"[ok] set hwbreak @ {GLYPH_RENDER:#x} (Thumb)")
    c.clear_hw_break(GLYPH_RENDER, kind=2)
    print("[ok] cleared hwbreak")
    # Read a chunk of VRAM
    vram = c.read_mem(VRAM_BASE, 128)
    print(f"[ok] read {len(vram)} bytes of VRAM (sample {vram[:8].hex()})")
    c.detach(); c.close()
    print("[ok] selftest passed")


def cmd_capture(args):
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    c = GDBClient(timeout=30.0)
    c.connect()
    print("[connected]")
    # qSupported handshake — many stubs need this before complex packets
    c.cmd("qSupported:swbreak+;hwbreak+")
    # If the game is already running (previous detach), interrupt first.
    c._send_raw(b"\x03")
    try: c._read_packet()
    except Exception: pass
    # Set glyph-render breakpoint (Thumb).
    c.set_hw_break(GLYPH_RENDER, kind=2)
    print(f"[hwbreak] set @ {GLYPH_RENDER:#x} (glyph render entry, Thumb)")

    tokens: list[dict] = []
    vram_snapshots: list[dict] = []
    halt = {"flag": False}

    def _sigint(*_):
        halt["flag"] = True
        print("\n[ctrl-c] requested stop; will flush after next break")

    signal.signal(signal.SIGINT, _sigint)

    last_snapshot_t = time.time()
    snapshot_period = max(0.25, args.snapshot_period)
    quiet_timeout = max(0.1, args.quiet_timeout)

    last_break_t = time.time()
    try:
        while not halt["flag"]:
            # Continue until breakpoint or quiet
            try:
                c.sock.settimeout(quiet_timeout)  # type: ignore
                stop = c.cont()
            except Exception:
                # Timed out without a break — possibly user is in a non-dialog
                # state; snapshot VRAM and keep looping.
                stop = ""
            now = time.time()
            if stop.startswith("T") or stop.startswith("S"):
                # Hit at glyph-render entry. r0 packs (page,idx).
                regs = c.read_regs()
                r0 = regs[0]
                page = r0 & 0xF
                idx  = (r0 >> 4) & 0xFFF
                # Sanity: ignore if page outside 1..7 (engine fires for ASCII too
                # but only Korean tokens are interesting).
                tokens.append({
                    "t": now,
                    "r0": r0,
                    "page": page,
                    "idx": idx,
                    "pc": regs[15],
                })
                last_break_t = now
                if len(tokens) % 25 == 0:
                    print(f"[capture] tokens={len(tokens)} latest=(page={page},idx={idx})")

            # Periodic VRAM snapshot
            if now - last_snapshot_t >= snapshot_period:
                try:
                    # Pause: SIGINT-equivalent — send '\x03' (break)
                    c.sock.settimeout(2.0)  # type: ignore
                    c._send_raw(b"\x03")
                    # Read stop reply
                    try: c._read_packet()
                    except Exception: pass
                    vram = c.read_mem(VRAM_BASE, VRAM_BG_BYTES)
                    groups = visible_tile_groups(vram)
                    snap_record = {
                        "t": now,
                        "token_index": len(tokens),
                        "groups": [
                            {
                                "line": g[0], "pos": g[1],
                                "tiles": [g[2], g[3], g[4], g[5]],
                                "fps": fingerprint_all_charblocks(vram, g[2], g[3], g[4], g[5]),
                            }
                            for g in groups
                        ],
                    }
                    vram_snapshots.append(snap_record)
                    last_snapshot_t = now
                    print(f"[snapshot] groups={len(groups)} (after {len(tokens)} tokens)")
                except Exception as e:
                    print(f"[snapshot-err] {e}")
    finally:
        # Flush
        try: c.clear_hw_break(GLYPH_RENDER, kind=2)
        except Exception: pass
        try: c.detach()
        except Exception: pass
        c.close()
        out = {
            "rom": "Pocket Monsters - LeafGreen (Korean).gba",
            "engine_entry": ENGINE_ENTRY,
            "tokens": tokens,
            "snapshots": vram_snapshots,
        }
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[saved] {out_path} ({len(tokens)} tokens, {len(vram_snapshots)} snapshots)")


def cmd_build_map(args):
    """Pair tokens with VRAM snapshots to derive (page,idx) -> fingerprint."""
    pair_counts: dict[tuple[int,int,str], int] = {}
    for trace_path in args.traces:
        data = json.loads(Path(trace_path).read_text())
        snaps = data.get("snapshots", [])
        tokens = data.get("tokens", [])
        # naive pairing: walk snapshots in order; for each snapshot,
        # consider tokens since previous snapshot in order; map them onto
        # newly-non-zero tile groups in the snapshot.
        prev_groups: set[tuple[int,int]] = set()
        prev_token_idx = 0
        for snap in snaps:
            cur_groups = [(g["line"], g["pos"], g["fps"][0]) for g in snap["groups"]]
            cur_keys = {(l,p) for l,p,_ in cur_groups}
            new_keys = [(l,p,fp) for l,p,fp in cur_groups if (l,p) not in prev_groups]
            new_tokens = tokens[prev_token_idx:snap["token_index"]]
            # filter to actual hangul tokens (page 1..6)
            han = [(t["page"], t["idx"]) for t in new_tokens if 1 <= t["page"] <= 6]
            # map in order
            for (l,p,fp), (page, idx) in zip(new_keys, han):
                key = (page, idx, fp)
                pair_counts[key] = pair_counts.get(key, 0) + 1
            prev_groups = cur_keys
            prev_token_idx = snap["token_index"]
    # Resolve: keep most frequent fp per (page,idx)
    by_key: dict[tuple[int,int], dict[str,int]] = {}
    for (page,idx,fp), c in pair_counts.items():
        by_key.setdefault((page,idx), {})[fp] = c
    out = {}
    for (page,idx), fps in by_key.items():
        best_fp, best_c = max(fps.items(), key=lambda kv: kv[1])
        out[f"F{page},{idx}"] = {"fp": best_fp, "count": best_c, "alts": fps}
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[built] {len(out)} (page,idx)→fp entries → {args.out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest", help="Verify GDB stub plumbing.")
    p_cap = sub.add_parser("capture", help="Capture token stream + VRAM snapshots.")
    p_cap.add_argument("--out", default=".moneo-artifacts/trace.json")
    p_cap.add_argument("--snapshot-period", type=float, default=2.0)
    p_cap.add_argument("--quiet-timeout", type=float, default=0.5)
    p_bm = sub.add_parser("build-map", help="Build (page,idx)→fp map from traces.")
    p_bm.add_argument("--traces", nargs="+", required=True)
    p_bm.add_argument("--out", default=".moneo-artifacts/runtime-charmap.json")
    args = ap.parse_args()
    {"selftest": cmd_selftest, "capture": cmd_capture, "build-map": cmd_build_map}[args.cmd](args)


if __name__ == "__main__":
    main()
