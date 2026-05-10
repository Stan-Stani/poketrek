#!/usr/bin/env python3
"""Reduce the trace_glyph_writes.lua output into composer call sites.

Inputs: /tmp/poketrek_trace/trace.jsonl
Outputs: stdout report + /tmp/poketrek_trace/composer_anchors.json

For each unique PC seen in the trace:
  - count of events
  - distribution of LR (caller-return PC)
  - distinct r0..r3 values seen at the moment of the write
  - cache addresses written to
  - 32-byte capstone disassembly window around PC
"""
from __future__ import annotations
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_ARM
except ImportError:
    print("pip install capstone", file=sys.stderr); sys.exit(1)

ROM = Path(__file__).resolve().parent / "leafgreen_J-K_2024.gba"
TRACE = Path("/tmp/poketrek_trace/trace.jsonl")
OUT = Path("/tmp/poketrek_trace/composer_anchors.json")
GBA_BASE = 0x08000000


def addr_to_off(a: int) -> int:
    return a - GBA_BASE


def load_events():
    events = []
    with TRACE.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events


def disasm_around(rom: bytes, pc: int, before: int = 16, after: int = 16) -> list[str]:
    """Disassemble Thumb instructions in [pc-before, pc+after]."""
    if pc & 1:
        # PC has Thumb bit set in some traces; mask it off.
        pc &= ~1
    off = addr_to_off(pc)
    if off < 0 or off >= len(rom):
        return [f"  (pc {pc:08x} not in ROM)"]
    start = max(0, off - before)
    end = min(len(rom), off + after + 2)
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    out = []
    for ins in md.disasm(rom[start:end], GBA_BASE + start):
        marker = " <--- PC" if ins.address == pc else ""
        out.append(f"  {ins.address:08x}: {ins.mnemonic:<6} {ins.op_str}{marker}")
    return out


def main():
    if not TRACE.exists():
        print(f"trace not found: {TRACE}", file=sys.stderr); sys.exit(1)
    rom = ROM.read_bytes()
    events = load_events()
    print(f"# total events: {len(events)}")

    by_pc: dict[int, list[dict]] = defaultdict(list)
    for ev in events:
        by_pc[ev["pc"]].append(ev)

    # Sort by frequency, descending.
    pc_freq = Counter({pc: len(evs) for pc, evs in by_pc.items()})

    print(f"# distinct PCs: {len(by_pc)}")
    print()

    anchors = []
    for pc, count in pc_freq.most_common(20):
        evs = by_pc[pc]
        lrs = Counter(ev["lr"] for ev in evs)
        cache_addrs = Counter()
        for ev in evs:
            for d in ev["diffs"]:
                cache_addrs[d["addr"]] += 1
        r0s = Counter(ev["r0"] for ev in evs)
        r1s = Counter(ev["r1"] for ev in evs)
        r2s = Counter(ev["r2"] for ev in evs)
        r3s = Counter(ev["r3"] for ev in evs)
        # For non-PC registers, find ones that look like ROM pointers
        # (>=0x08000000 and <=0x09FFFFFF).
        rom_ptrs_seen = Counter()
        for reg in ("r4", "r5", "r6", "r7", "r8", "r9", "r10", "r11"):
            for ev in evs:
                v = ev[reg]
                if 0x08000000 <= v <= 0x09FFFFFF:
                    rom_ptrs_seen[(reg, v)] += 1

        print("=" * 70)
        print(f"PC {pc:08x}  events={count}")
        print(f"  distinct LRs ({len(lrs)}): " +
              ", ".join(f"{lr:08x}x{n}" for lr, n in lrs.most_common(5)))
        print(f"  cache write addrs (top 10):")
        for a, n in cache_addrs.most_common(10):
            print(f"    {a:08x} x{n}")
        print(f"  r0 distinct values (top 5): " +
              ", ".join(f"{v:08x}x{n}" for v, n in r0s.most_common(5)))
        print(f"  r1 distinct values (top 5): " +
              ", ".join(f"{v:08x}x{n}" for v, n in r1s.most_common(5)))
        print(f"  r2 distinct values (top 5): " +
              ", ".join(f"{v:08x}x{n}" for v, n in r2s.most_common(5)))
        print(f"  r3 distinct values (top 5): " +
              ", ".join(f"{v:08x}x{n}" for v, n in r3s.most_common(5)))
        print(f"  ROM-pointer-looking regs (top 8):")
        for (reg, v), n in rom_ptrs_seen.most_common(8):
            print(f"    {reg}={v:08x} x{n}")
        print(f"  disasm around PC:")
        for line in disasm_around(rom, pc, before=24, after=24):
            print(line)

        anchors.append({
            "pc": pc,
            "events": count,
            "top_lrs": [(lr, n) for lr, n in lrs.most_common(5)],
            "cache_addrs": [(a, n) for a, n in cache_addrs.most_common(20)],
            "r0_top": [(v, n) for v, n in r0s.most_common(10)],
            "r1_top": [(v, n) for v, n in r1s.most_common(10)],
            "r2_top": [(v, n) for v, n in r2s.most_common(10)],
            "r3_top": [(v, n) for v, n in r3s.most_common(10)],
            "rom_ptr_regs": [(f"{reg}={v:08x}", n)
                             for (reg, v), n in rom_ptrs_seen.most_common(20)],
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(anchors, indent=2))
    print(f"\n# wrote {OUT}")

    # Cluster LRs (caller return points) — these are the composer entry
    # points one frame up.
    print("\n" + "=" * 70)
    print("# LR distribution across all events (Thumb +1 expected)")
    all_lrs: Counter[int] = Counter()
    for ev in events:
        all_lrs[ev["lr"]] += 1
    for lr, n in all_lrs.most_common(20):
        target = lr & ~1
        # Disasm the byte right BEFORE lr (the BL we returned from).
        off = addr_to_off(target) - 4
        if off < 0:
            print(f"  lr={lr:08x} x{n}  (target out of ROM)")
            continue
        # Resolve the BL by reading 4 bytes ending at target-0.
        md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
        ins = list(md.disasm(rom[off:off + 4], GBA_BASE + off))
        if ins and ins[0].mnemonic in ("bl", "blx"):
            print(f"  lr={lr:08x} x{n}  caller {ins[0].address:08x}: " +
                  f"{ins[0].mnemonic} {ins[0].op_str}")
        else:
            print(f"  lr={lr:08x} x{n}  (no BL at {GBA_BASE + off:08x})")


if __name__ == "__main__":
    main()
