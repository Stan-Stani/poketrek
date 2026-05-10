#!/usr/bin/env python3
"""Disassemble Thumb code around a given GBA address.

Usage: disasm_around.py 08003028 [--bytes 200]
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB

ROM = Path(__file__).resolve().parent / "leafgreen_J-K_2024.gba"
GBA_BASE = 0x08000000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("addr", help="hex address (with or without 0x)")
    ap.add_argument("--bytes", type=lambda s: int(s, 0), default=0x100,
                    help="bytes to disassemble forward")
    ap.add_argument("--before", type=lambda s: int(s, 0), default=0x10,
                    help="bytes to disassemble before")
    ap.add_argument("--literals", action="store_true",
                    help="resolve LDR Rd, [PC, #imm] literal pool entries")
    args = ap.parse_args()

    rom = ROM.read_bytes()
    addr = int(args.addr.replace("0x", ""), 16)
    if addr & 1:
        addr &= ~1
    off = addr - GBA_BASE
    if off < 0 or off >= len(rom):
        print(f"addr {addr:08x} out of ROM", file=sys.stderr); sys.exit(1)
    start = max(0, off - args.before)
    end = min(len(rom), off + args.bytes)
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    md.detail = True
    for ins in md.disasm(rom[start:end], GBA_BASE + start):
        marker = " <---" if ins.address == addr else ""
        line = f"{ins.address:08x}: {ins.mnemonic:<6} {ins.op_str}{marker}"
        if args.literals and ins.mnemonic == "ldr" and "[pc," in ins.op_str:
            # Resolve literal: pool addr = (pc & ~3) + 4 + imm
            try:
                imm_hex = ins.op_str.rsplit("#", 1)[-1].rstrip("]")
                imm = int(imm_hex, 0)
                pool = ((ins.address + 4) & ~3) + imm
                pool_off = pool - GBA_BASE
                if 0 <= pool_off + 4 <= len(rom):
                    val = int.from_bytes(rom[pool_off:pool_off + 4], "little")
                    line += f"   ; pool@{pool:08x}=0x{val:08x}"
            except Exception:
                pass
        print(line)


if __name__ == "__main__":
    main()
