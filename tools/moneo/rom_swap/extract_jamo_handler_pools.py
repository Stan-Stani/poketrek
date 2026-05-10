#!/usr/bin/env python3
"""Extract literal-pool entries from each of the 6 jamo handlers in the
2024 dispatcher: 800645c, 8006504, 80065cc, 8006738, 8006800, 800696c.
Print every PC-relative LDR's resolved value, and the ARM-multiplier
fingerprint (lsls Rn, #X) just before, so we can identify font strides
and per-handler bitmap base addresses.
"""
from __future__ import annotations
from pathlib import Path
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB

ROM = Path(__file__).resolve().parent / "leafgreen_J-K_2024.gba"
GBA_BASE = 0x08000000
data = ROM.read_bytes()
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)

HANDLERS = [
    0x0800645c,
    0x08006504,
    0x080065cc,
    0x08006738,
    0x08006800,
    0x0800696c,
]

# Walk forward to first pop {pc} or bx lr to find function end.
def function_end(start: int, max_len: int = 0x300) -> int:
    off = start - GBA_BASE
    for ins in md.disasm(data[off:off + max_len], start):
        if ins.mnemonic == "pop" and "pc" in ins.op_str:
            return ins.address + ins.size
        if ins.mnemonic == "bx" and "lr" in ins.op_str:
            return ins.address + ins.size
    return start + max_len

for handler in HANDLERS:
    end = function_end(handler)
    print(f"\n{'='*70}")
    print(f"HANDLER {handler:08x} -- {end:08x} (len={end - handler})")
    print('='*70)
    off = handler - GBA_BASE
    last_imm_shift = None
    for ins in md.disasm(data[off:off + (end - handler) + 4], handler):
        # Track the most recent lsls Rn, Rm, #imm preceding an LDR
        if ins.mnemonic == "lsls" and "#" in ins.op_str:
            try:
                last_imm_shift = ins.op_str.split("#")[-1]
            except Exception:
                pass
        line = f"  {ins.address:08x}: {ins.mnemonic:<6} {ins.op_str}"
        if ins.mnemonic == "ldr" and "[pc," in ins.op_str:
            try:
                imm_hex = ins.op_str.rsplit("#", 1)[-1].rstrip("]")
                imm = int(imm_hex, 0)
                pool = ((ins.address + 4) & ~3) + imm
                pool_off = pool - GBA_BASE
                if 0 <= pool_off + 4 <= len(data):
                    val = int.from_bytes(data[pool_off:pool_off + 4], "little")
                    line += f"   ; pool=0x{val:08x}"
                    if 0x08000000 <= val < 0x0a000000:
                        # In ROM space; flag patched region
                        if val >= 0x08d00000:
                            line += "  [PATCHED]"
            except Exception:
                pass
        print(line)
