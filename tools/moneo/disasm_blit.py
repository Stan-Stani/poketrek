#!/usr/bin/env python3
"""Disassemble the blit function at 0x08002F5C to understand the lookup table."""
import capstone
from pathlib import Path

ROM = bytearray(Path("Pocket Monsters - LeafGreen (Korean).gba").read_bytes())

def thumb_disasm(file_off, count=80):
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    md.detail = True
    data = bytes(ROM[file_off: file_off + count*2])
    gba_off = 0x08000000 + file_off
    print(f"Disassembly at file_off={file_off:#x} (GBA addr {gba_off:#x}):")
    for insn in md.disasm(data, gba_off):
        print(f"  {insn.address:#010x}: {insn.mnemonic:10s} {insn.op_str}")

# The blit function at 0x8002F5C (file 0x2F5C)
print("=== Blit function at 0x08002F5C ===")
thumb_disasm(0x2F5C, 100)
