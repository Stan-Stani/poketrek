#!/usr/bin/env python3
"""Find every Thumb BL caller of the LZ77 BIOS wrappers and resolve r0/r1.

Wrappers (located via byte-pattern svc #imm; bx lr):
  - LZ77UnCompVram  @ 0x081e3bb8 (file 0x1e3bb8)
  - LZ77UnCompWram  @ 0x081e3bbc (file 0x1e3bbc)

For each BL <wrapper> in the ROM, walk back ~80 instructions and find the
last LDR Rd, [PC, #imm] that wrote into r0 (compressed source) and r1
(destination). Resolve each literal-pool target and emit a structured
report.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

try:
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
except ImportError:
    print("pip install capstone", file=sys.stderr); sys.exit(1)

ROM = Path(__file__).resolve().parent / "leafgreen_J-K_2024.gba"
OUT = Path(__file__).resolve().parent / "lz77_callers_2024.json"
GBA_BASE = 0x08000000
WRAPPERS = {
    0x081e3bb8: "LZ77UnCompVram",
    0x081e3bbc: "LZ77UnCompWram",
}
LOOKBACK = 200

VRAM = (0x06000000, 0x06020000)
EWRAM = (0x02000000, 0x02040000)
IWRAM = (0x03000000, 0x03008000)
ROM_VANILLA = (0x08000000, 0x08800000)
ROM_PATCHED = (0x08D00000, 0x09000000)


def classify(a: int | None) -> str:
    if a is None:
        return "?"
    for name, (lo, hi) in [("VRAM", VRAM), ("EWRAM", EWRAM), ("IWRAM", IWRAM),
                           ("ROM_VANILLA", ROM_VANILLA), ("ROM_PATCHED", ROM_PATCHED)]:
        if lo <= a < hi:
            return name
    return f"OTHER({a:#x})"


def decode_bl(hw1: int, hw2: int) -> int | None:
    """Thumb-1 BL: HW1=0xF000|hi11, HW2=0xF800|lo11. Returns signed offset."""
    if (hw1 & 0xF800) != 0xF000 or (hw2 & 0xF800) != 0xF800:
        return None
    hi = hw1 & 0x7FF
    lo = hw2 & 0x7FF
    if hi & 0x400:
        hi -= 0x800  # sign-extend 11 bits
    return (hi << 12) | (lo << 1)


def find_bl_callers(data: bytes, target_gba: int) -> list[int]:
    """Return file offsets of BL <target_gba> instructions."""
    target_file = target_gba - GBA_BASE
    out = []
    # BL HW1 first byte is 0xF0..0xF7; second byte's high nibble is F (0xF0..0xF7).
    # Easier: iterate at 2-byte stride.
    for i in range(0, len(data) - 4, 2):
        hw1 = int.from_bytes(data[i:i+2], "little")
        if (hw1 & 0xF800) != 0xF000:
            continue
        hw2 = int.from_bytes(data[i+2:i+4], "little")
        off = decode_bl(hw1, hw2)
        if off is None:
            continue
        # PC at first halfword of BL = i + 4 (two-halfword instruction).
        target = i + 4 + off
        # Wrap to file offset (still in ROM space)
        if 0 <= target < len(data) and target == target_file:
            out.append(i)
    return out


def resolve_pc_relative(data: bytes, ldr_addr: int, imm: int) -> int | None:
    pc = (ldr_addr + 4) & ~0x3
    t = pc + imm
    if t + 4 > len(data):
        return None
    return int.from_bytes(data[t:t+4], "little")


def analyze_caller(data: bytes, bl_addr: int):
    """Disassemble the LOOKBACK bytes ending exactly at bl_addr and find LDRs."""
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    md.detail = False

    best = None
    for off in range(0, LOOKBACK, 2):
        base = bl_addr - LOOKBACK + off
        if base < 0:
            continue
        ins = list(md.disasm(data[base:bl_addr+4], base))
        if not ins:
            continue
        if ins[-1].address != bl_addr:
            continue
        if not ins[-1].mnemonic.startswith("bl"):
            continue
        if best is None or len(ins) > len(best):
            best = ins

    if best is None:
        return None

    last = {0: None, 1: None, 2: None, 3: None}
    last_ldr_addr = {0: None, 1: None, 2: None, 3: None}
    for ins in best:
        if ins.mnemonic.startswith("ldr"):
            m = re.match(r"r(\d+),\s*\[pc,\s*#?(0x[0-9a-fA-F]+|\d+)\]", ins.op_str)
            if m:
                rn = int(m.group(1))
                if rn in last:
                    immv = int(m.group(2), 0)
                    last[rn] = resolve_pc_relative(data, ins.address, immv)
                    last_ldr_addr[rn] = ins.address
        elif ins.mnemonic == "movs" or ins.mnemonic == "mov":
            # Reset tracking if r0/r1 gets overwritten by something other than a load
            m2 = re.match(r"r(\d+),\s*r(\d+)", ins.op_str)
            if m2:
                rn = int(m2.group(1))
                if rn in last and last[rn] is not None:
                    # value tainted; clear
                    last[rn] = None
                    last_ldr_addr[rn] = None
    return {
        "bl_file_off": bl_addr,
        "bl_gba_addr": bl_addr + GBA_BASE,
        "r0_lit": last[0],
        "r1_lit": last[1],
        "r0_ldr_off": last_ldr_addr[0],
        "r1_ldr_off": last_ldr_addr[1],
        "tail": [(hex(i.address), i.mnemonic, i.op_str) for i in best[-12:]],
    }


def main():
    data = ROM.read_bytes()
    print(f"Loaded {ROM.name} ({len(data):#x} bytes)\n")

    all_results = []
    for gba_addr, name in WRAPPERS.items():
        print(f"=== {name} @ {gba_addr:#x} ===")
        callers = find_bl_callers(data, gba_addr)
        print(f"  {len(callers)} BL caller sites")
        for c in callers:
            r = analyze_caller(data, c)
            if r:
                r["wrapper"] = name
                all_results.append(r)

    print(f"\nTotal analyzed callers: {len(all_results)}")

    # Group by interest
    interesting = []
    for r in all_results:
        s_cls = classify(r["r0_lit"])
        d_cls = classify(r["r1_lit"])
        r["src_cls"] = s_cls
        r["dst_cls"] = d_cls
        score = 0
        if s_cls == "ROM_PATCHED": score += 100
        if d_cls == "VRAM": score += 50
        if d_cls in ("EWRAM", "IWRAM"): score += 30
        if s_cls == "ROM_VANILLA": score += 5
        r["score"] = score
        if score >= 50:
            interesting.append(r)

    interesting.sort(key=lambda r: -r["score"])
    print(f"\nInteresting (src in ROM ∧ dst in V/E/IWRAM): {len(interesting)}\n")
    print(f"{'bl_off':>10} {'bl_gba':>10} {'wrapper':>16}  "
          f"{'src':>10} {'src_cls':>12} {'dst':>10} {'dst_cls':>12}")
    for r in interesting:
        print(f"{r['bl_file_off']:>10x} {r['bl_gba_addr']:>10x} {r['wrapper']:>16}  "
              f"{(r['r0_lit'] or 0):>10x} {r['src_cls']:>12} "
              f"{(r['r1_lit'] or 0):>10x} {r['dst_cls']:>12}")

    OUT.write_text(json.dumps(all_results, indent=2))
    print(f"\nFull dump: {OUT}")


if __name__ == "__main__":
    main()
