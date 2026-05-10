#!/usr/bin/env python3
"""Locate LZ77UnCompVRAM/WRAM call sites and resolve their literal-pool args.

Strategy. For each `SVC #0x12` (or `#0x11`) in Thumb code, walk back ~80
instructions and collect every `LDR Rd, [PC, #imm]` we see. Resolve each
literal-pool target. The last LDR into r0 before the SVC is the source
pointer (compressed data); the last into r1 is the destination.

Sane sites get filtered to:
- destination in VRAM tile region (0x06000000..0x0601FFFF), OR EWRAM/IWRAM
- source pointer in patched region (>= 0x08D00000) — those are NEW Korean
  assets layered on top of vanilla FR/LG.

Output: a JSON dump of all hits with resolved args + a brief stdout report.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

try:
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
except ImportError:
    print("capstone is required: pip install capstone", file=sys.stderr)
    sys.exit(1)

ROM_PATH = Path(__file__).resolve().parent / "leafgreen_J-K_2024.gba"
OUT_PATH = Path(__file__).resolve().parent / "lz77_sites_2024.json"
GBA_BASE = 0x08000000
PATCHED_LO = 0x08D00000
PATCHED_HI = 0x09000000
VRAM_LO = 0x06000000
VRAM_HI = 0x06020000
EWRAM_LO = 0x02000000
EWRAM_HI = 0x02040000
IWRAM_LO = 0x03000000
IWRAM_HI = 0x03008000

LOOKBACK_BYTES = 160  # ~80 Thumb instructions


def find_swi(data: bytes, imm: int) -> list[int]:
    # Thumb halfword is LE: SVC #imm8 = halfword 0xDFxx → bytes [imm, 0xDF].
    pat = bytes([imm, 0xDF])
    return [m.start() for m in re.finditer(re.escape(pat), data) if m.start() % 2 == 0]


def resolve_pc_relative_ldr(data: bytes, ins_addr_file: int, imm: int) -> int | None:
    """Thumb LDR Rd, [PC, #imm] reads from (align(PC+4,4) + imm).
    PC during execution = instruction_addr + 4 (in Thumb).
    `ins_addr_file` is the file offset; the same PC-relative arithmetic
    works in file-offset space.
    """
    pc = (ins_addr_file + 4) & ~0x3
    target = pc + imm
    if target + 4 > len(data):
        return None
    return int.from_bytes(data[target:target + 4], "little")


def analyze(data: bytes, swi_addr: int, imm: int):
    """Disassemble the window before swi_addr; collect LDRs into r0, r1."""
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    md.detail = True
    start = max(0, swi_addr - LOOKBACK_BYTES)
    window = data[start:swi_addr + 2]

    # Try disassembling from each 2-byte alignment in the window; prefer the
    # offset that yields the longest coherent run ending exactly at swi_addr.
    best = None
    for off in range(0, LOOKBACK_BYTES, 2):
        base_file = start + off
        if base_file >= swi_addr:
            break
        ins_list = list(md.disasm(window[off:], base_file))
        if not ins_list:
            continue
        # Reject if the run misses the SWI byte exactly.
        last = ins_list[-1]
        if last.address + last.size != swi_addr + 2:
            continue
        # Confirm the last instruction is the SVC.
        if last.mnemonic != "svc" and last.mnemonic != "swi":
            continue
        # Score by run length.
        if best is None or len(ins_list) > len(best):
            best = ins_list
    if best is None:
        return None

    last_r0 = None
    last_r1 = None
    last_r0_lit = None
    last_r1_lit = None
    for ins in best:
        if ins.mnemonic.startswith("ldr"):
            ops = ins.op_str
            # Match "rN, [pc, #0xNN]" or capstone-resolved "rN, [0xNN]".
            m_pc = re.match(r"r(\d+),\s*\[pc,\s*#(0x[0-9a-f]+|\d+)\]", ops, re.I)
            if m_pc:
                rn = int(m_pc.group(1))
                immv = int(m_pc.group(2), 0)
                lit = resolve_pc_relative_ldr(data, ins.address, immv)
                if rn == 0:
                    last_r0_lit = lit
                    last_r0 = ins.address
                elif rn == 1:
                    last_r1_lit = lit
                    last_r1 = ins.address

    return {
        "swi_file_off": swi_addr,
        "swi_imm": imm,
        "r0_ldr_file_off": last_r0,
        "r0_lit": last_r0_lit,
        "r1_ldr_file_off": last_r1,
        "r1_lit": last_r1_lit,
        "instructions": [(hex(i.address), i.mnemonic, i.op_str) for i in best],
    }


def classify(addr: int | None) -> str:
    if addr is None:
        return "unknown"
    if VRAM_LO <= addr < VRAM_HI:
        return "VRAM"
    if EWRAM_LO <= addr < EWRAM_HI:
        return "EWRAM"
    if IWRAM_LO <= addr < IWRAM_HI:
        return "IWRAM"
    if PATCHED_LO <= addr < PATCHED_HI:
        return "ROM_PATCHED"
    if GBA_BASE <= addr < PATCHED_LO:
        return "ROM_VANILLA"
    return f"OTHER({addr:#x})"


def main():
    data = ROM_PATH.read_bytes()
    print(f"Loaded {ROM_PATH.name} ({len(data):#x} bytes)")

    results = []
    for imm in (0x12, 0x11):
        sites = find_swi(data, imm)
        print(f"\n=== SVC #{imm:#x} sites: {len(sites)} candidates ===")
        for s in sites:
            r = analyze(data, s, imm)
            if r is None:
                continue
            results.append(r)

    # Sort by interest: source in patched region + dest in VRAM first.
    def score(r):
        s = r.get("r0_lit")
        d = r.get("r1_lit")
        s_cls = classify(s)
        d_cls = classify(d)
        prio = 0
        if s_cls == "ROM_PATCHED":
            prio += 100
        if d_cls == "VRAM":
            prio += 50
        if s_cls == "ROM_VANILLA":
            prio += 10
        return -prio

    results.sort(key=score)

    # Stdout summary.
    print(f"\n=== {len(results)} confirmed SVC sites with disassembled context ===")
    print(f"{'swi_off':>10} {'imm':>5} {'src_lit':>12} {'src_cls':>14} {'dst_lit':>12} {'dst_cls':>14}")
    interesting = 0
    for r in results:
        s = r.get("r0_lit")
        d = r.get("r1_lit")
        s_cls = classify(s)
        d_cls = classify(d)
        if s_cls in ("ROM_PATCHED", "ROM_VANILLA") and d_cls in ("VRAM", "EWRAM", "IWRAM"):
            interesting += 1
            print(f"{r['swi_file_off']:>10x} {r['swi_imm']:>5x} "
                  f"{(s or 0):>12x} {s_cls:>14} {(d or 0):>12x} {d_cls:>14}")
    print(f"\n{interesting} sites have plausible source+dest types.")

    OUT_PATH.write_text(json.dumps(results, indent=2))
    print(f"Full dump → {OUT_PATH}")


if __name__ == "__main__":
    main()
