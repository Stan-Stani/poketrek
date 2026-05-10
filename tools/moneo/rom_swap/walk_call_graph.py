#!/usr/bin/env python3
"""Walk the call graph backward from a starting address.

Given a file offset inside a function, find:
1. The function's entry point (nearest preceding `push` instruction).
2. All BL sites in the ROM that target that function.
3. For each caller, recurse N levels.

Used to climb from the BL LZ77UnCompWram site at file 0x9f850 up to the
text-rendering dispatcher. Each level out gives more context.
"""
from __future__ import annotations
import argparse
import sys
from collections import defaultdict
from pathlib import Path

try:
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
except ImportError:
    print("pip install capstone", file=sys.stderr); sys.exit(1)

ROM = Path(__file__).resolve().parent / "leafgreen_J-K_2024.gba"
GBA_BASE = 0x08000000


def find_function_start(data: bytes, addr: int) -> int:
    """Walk back to the nearest `push {...}` Thumb instruction.
    Heuristic: any push that includes lr (push ... lr).
    """
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    # Try every 2-byte alignment as a potential function start.
    # Walk backward (highest addr first) so we find the closest preceding
    # push — the actual function entry — not an earlier one.
    for off in range(addr - 2, max(0, addr - 0x300), -2):
        ins = list(md.disasm(data[off:off + 2], off))
        if not ins:
            continue
        i = ins[0]
        if i.mnemonic != "push":
            continue
        if "lr" not in i.op_str:
            continue
        # Verify by disassembling forward — we should reach addr without
        # a pop/bx in between
        run = list(md.disasm(data[off:addr + 2], off))
        if not run:
            continue
        if run[-1].address > addr:
            continue
        ok = True
        for ri in run:
            if ri.address >= addr:
                break
            # function end markers: pop {... pc} or bx lr
            if ri.mnemonic == "pop" and "pc" in ri.op_str:
                ok = False; break
            if ri.mnemonic == "bx" and "lr" in ri.op_str:
                ok = False; break
        if ok:
            return off
    return -1  # fallback


def find_function_end(data: bytes, start: int, max_len: int = 0x1000) -> int:
    """Walk forward to the first `pop {...pc}` or `bx lr` we hit."""
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    ins = list(md.disasm(data[start:start + max_len], start))
    for i in ins:
        if i.mnemonic == "pop" and "pc" in i.op_str:
            return i.address + i.size
        if i.mnemonic == "bx" and "lr" in i.op_str:
            return i.address + i.size
    return start + max_len


def decode_bl(hw1: int, hw2: int) -> int | None:
    if (hw1 & 0xF800) != 0xF000 or (hw2 & 0xF800) != 0xF800:
        return None
    hi = hw1 & 0x7FF
    lo = hw2 & 0x7FF
    if hi & 0x400:
        hi -= 0x800
    return (hi << 12) | (lo << 1)


def find_bl_callers(data: bytes, target_file_off: int) -> list[int]:
    """Return all file offsets where `BL <target>` appears."""
    out = []
    for i in range(0, len(data) - 4, 2):
        hw1 = int.from_bytes(data[i:i + 2], "little")
        if (hw1 & 0xF800) != 0xF000:
            continue
        hw2 = int.from_bytes(data[i + 2:i + 4], "little")
        off = decode_bl(hw1, hw2)
        if off is None:
            continue
        target = i + 4 + off
        if target == target_file_off:
            out.append(i)
    return out


def find_pointer_refs(data: bytes, target_file_off: int) -> list[int]:
    """Return all 4-byte-aligned u32 offsets in ROM whose value points at
    target_file_off + 1 (Thumb function pointer convention) or target_file_off.
    These are entries in function-pointer tables / dispatch tables.
    """
    target_gba_thumb = (target_file_off + GBA_BASE) | 1
    target_gba_arm = target_file_off + GBA_BASE
    needle_t = target_gba_thumb.to_bytes(4, "little")
    needle_a = target_gba_arm.to_bytes(4, "little")
    out = []
    pos = 0
    while True:
        i_t = data.find(needle_t, pos)
        i_a = data.find(needle_a, pos)
        candidates = [i for i in (i_t, i_a) if i != -1]
        if not candidates:
            break
        i = min(candidates)
        if i % 4 == 0:
            out.append(i)
        pos = i + 1
    return out


def collect_pc_literals(data: bytes, start: int, end: int) -> list[tuple[int, int]]:
    """Return list of (instruction_addr, resolved_u32_literal) for every
    `LDR Rn, [PC, #imm]` in the function body."""
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    out = []
    ins = list(md.disasm(data[start:end], start))
    import re
    for i in ins:
        if not i.mnemonic.startswith("ldr"):
            continue
        m = re.match(r"r(\d+),\s*\[pc,\s*#?(0x[0-9a-fA-F]+|\d+)\]", i.op_str)
        if m:
            imm = int(m.group(2), 0) if m.group(2).startswith("0x") else int(m.group(2))
            pool = (i.address + 4) & ~3
            tgt = pool + imm
            if 0 <= tgt + 4 <= len(data):
                v = int.from_bytes(data[tgt:tgt + 4], "little")
                out.append((i.address, v))
    return out


def classify(v: int) -> str:
    if 0x02000000 <= v < 0x02040000: return "EWRAM"
    if 0x03000000 <= v < 0x03008000: return "IWRAM"
    if 0x06000000 <= v < 0x06020000: return "VRAM"
    if 0x08D00000 <= v < 0x09000000: return "ROM_PATCHED"
    if 0x08000000 <= v < 0x08800000: return "ROM_VANILLA"
    return "OTHER"


def walk(data: bytes, addr: int, depth: int = 0, max_depth: int = 4,
         visited: set | None = None):
    if visited is None: visited = set()
    if depth > max_depth: return
    indent = "  " * depth
    fs = find_function_start(data, addr)
    if fs == -1:
        print(f"{indent}? no function start found for {addr:#x}")
        return
    if fs in visited:
        print(f"{indent}↻ {fs:#x} already visited")
        return
    visited.add(fs)
    fe = find_function_end(data, fs)
    callers = find_bl_callers(data, fs)
    ptr_refs = find_pointer_refs(data, fs)
    lits = collect_pc_literals(data, fs, fe)

    print(f"{indent}→ FUNC {fs:#x}..{fe:#x} (size {fe-fs})  "
          f"{len(callers)} BL  {len(ptr_refs)} ptr-refs  {len(lits)} literals")
    if ptr_refs:
        print(f"{indent}  ptr-table refs at: ", end="")
        print(", ".join(f"{p:#x}" for p in ptr_refs[:10]))

    # Show ROM-region literals from this function
    rom_p_lits = [(ins, v) for ins, v in lits if classify(v) == "ROM_PATCHED"]
    rom_v_lits = [(ins, v) for ins, v in lits if classify(v) == "ROM_VANILLA"]
    ewram_lits = [(ins, v) for ins, v in lits if classify(v) == "EWRAM"]
    if rom_p_lits:
        print(f"{indent}  patched ROM literals: ", end="")
        print(", ".join(f"{v:#x}" for _, v in rom_p_lits[:8]))
    if ewram_lits:
        print(f"{indent}  EWRAM literals:  ",
              ", ".join(f"{v:#x}" for _, v in ewram_lits[:8]))

    if not callers:
        print(f"{indent}  ⊥ no callers (root)")
        return
    if len(callers) > 30:
        print(f"{indent}  many callers ({len(callers)}); showing first 5")
        callers = callers[:5]
    for c in callers:
        walk(data, c, depth + 1, max_depth, visited)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("addrs", nargs="+", help="Starting file offsets (hex)")
    ap.add_argument("--depth", type=int, default=3)
    args = ap.parse_args()
    data = ROM.read_bytes()
    for a in args.addrs:
        addr = int(a, 16)
        print(f"\n=========== Walking from {addr:#x} ===========")
        walk(data, addr, max_depth=args.depth)


if __name__ == "__main__":
    main()
