#!/usr/bin/env python3
"""Parse pokefirered's event.inc to extract the FRLG script-opcode table."""
from __future__ import annotations
import re
from pathlib import Path

EVENT_INC = Path.home() / ".cache/pokefirered/asm/macros/event.inc"

# Each opcode macro looks like:
#   .macro <name> [args]
#   .byte 0xXX                      # the opcode byte itself
#   [.byte ...]    [.2byte ...]     [.4byte ...]
#   .endm
#
# Some macros are PSEUDO-MACROS (composed of others); we identify a "real"
# opcode macro as one whose first directive after .macro is `.byte 0x..`.

DIRECTIVE_LEN = {".byte": 1, ".2byte": 2, ".4byte": 4, ".word": 4}


def parse_macros(text: str):
    """Yield (name, args_str, body_lines) for every .macro block."""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        m = re.match(r'\.macro\s+(\S+)(?:\s+(.*))?$', ln)
        if not m:
            i += 1
            continue
        name = m.group(1)
        args = (m.group(2) or "").strip()
        body = []
        i += 1
        while i < len(lines):
            inner = lines[i].strip()
            if inner == ".endm":
                break
            if inner and not inner.startswith("@"):
                body.append(inner)
            i += 1
        yield name, args, body
        i += 1


def opcode_info(body: list[str]) -> tuple[int | None, int | None, list[int]]:
    """Return (opcode_byte_or_None, total_byte_length_or_None, list_of_4byte_arg_offsets).
    Returns None for opcode if first directive isn't .byte 0xXX (pseudo-macro)."""
    if not body:
        return None, 0, []
    # First directive must be .byte 0xXX
    first = body[0]
    m = re.match(r'\.byte\s+0x([0-9a-fA-F]+)\b', first)
    if not m:
        return None, None, []
    opcode = int(m.group(1), 16)
    total = 1
    ptr_offsets: list[int] = []
    for d in body[1:]:
        # Strip any inline comment
        d = re.sub(r'@.*$', '', d).strip()
        if not d:
            continue
        # Skip control directives like .align, .global, etc.
        m2 = re.match(r'(\.byte|\.2byte|\.4byte|\.word)\b', d)
        if m2:
            sz = DIRECTIVE_LEN[m2.group(1)]
            if sz == 4:
                ptr_offsets.append(total)
            total += sz
            continue
        # Macro CALLs inside a macro -- e.g. trainerbattle calls trainerbattle_inner.
        # We can't statically expand; treat length as unknown.
        # But many simple opcodes don't have these.
        return opcode, None, ptr_offsets
    return opcode, total, ptr_offsets


def main():
    text = EVENT_INC.read_text()
    opcodes: dict[int, dict] = {}
    pseudo: list[str] = []
    for name, args, body in parse_macros(text):
        op, length, ptr_offs = opcode_info(body)
        if op is None:
            pseudo.append(name)
            continue
        opcodes[op] = {
            "mnemonic": name,
            "length": length,
            "ptr_offsets": ptr_offs,
            "args": args,
        }

    print(f"Real opcodes parsed: {len(opcodes)}")
    print(f"Pseudo-macros (composed): {len(pseudo)}")
    unknown_len = [op for op, info in opcodes.items() if info["length"] is None]
    print(f"Opcodes with unknown length: {len(unknown_len)}: {[hex(o) for o in unknown_len]}")
    unmapped = sorted(set(range(256)) - set(opcodes))
    print(f"Unmapped bytes 0x00-0xFF: {len(unmapped)}")

    # Generate Python module
    out_path = Path(__file__).parent / "script_opcodes.py"
    lines = [
        '"""Auto-generated FRLG script opcode table from pokefirered event.inc."""',
        '# DO NOT EDIT by hand -- regenerate via tools/moneo/_gen_opcodes.py',
        '',
        '# Each entry: opcode_byte -> {mnemonic, length, ptr_offsets, args}',
        '#   length=None means variable-length (handle specially)',
        '#   ptr_offsets are byte offsets within the instruction where 4-byte ROM ptrs live',
        'OPCODES: dict[int, dict] = {',
    ]
    for op in sorted(opcodes):
        info = opcodes[op]
        lines.append(
            f'    0x{op:02X}: {{"mnemonic": {info["mnemonic"]!r}, '
            f'"length": {info["length"]!r}, '
            f'"ptr_offsets": {info["ptr_offsets"]!r}, '
            f'"args": {info["args"]!r}}},'
        )
    lines.extend([
        '}',
        '',
        '# Opcodes that load text records (their ptr arg is a TEXT pointer):',
        'TEXT_LOADING_OPCODES = {',
        '    0x67: "message",         # text:4',
        '    0x78: "braillemessage",  # text:4',
        '    0x9B: "messageautoscroll",',
        '    0xBD: "vmessage",',
        '    0xBE: "vbuffermessage",',
        '    0xC8: "loadhelp",',
        '}',
        '',
        '# msgbox/msgbox_default/etc. are pseudo-macros expanding to:',
        '#   loadword 0, <text>     (0x0F 0x00 ptr:4) = 6 bytes',
        '#   callstd <type>         (0x09 type:1)     = 2 bytes',
        '# So when 0x0F has destIdx==0 followed by 0x09, the ptr is text.',
        'LOADWORD_OPCODE = 0x0F',
        'CALLSTD_OPCODE = 0x09',
        '',
        '# Control flow opcodes (recurse into pointer targets):',
        'CALL_GOTO_OPCODES = {0x04, 0x05}',
        'CALL_GOTO_IF_OPCODES = {0x06, 0x07}',
        '',
        '# Terminators (stop walking the script):',
        'END_OPCODES = {0x02, 0x03, 0x0C, 0x0D}  # end, return, returnram, endram',
        '',
        '# bufferstring (0x85) and vbufferstring (0xBF) have unusual layouts:',
        '#   .byte 0x85 / 0xBF',
        '#   stringvar <stringVarId>    -- the stringvar macro emits .byte stringVarId',
        '#   .4byte text',
        '# So total = 1 + 1 + 4 = 6 bytes, text ptr at offset +2.',
        'BUFFERSTRING_OPCODES = {0x85, 0xBF}  # ptr at +2, length 6',
        '',
        '# trainerbattle (0x5C): subtype byte at +1; layouts depend on subtype.',
        '# We hand-author these from the trainerbattle_* macros in event.inc:',
        'TRAINERBATTLE_LAYOUTS = {',
        '    # subtype: (length, [text_ptr_offsets])',
        '    0: (14, [6, 10]),  # _single: id:2, _:2, intro:4, lose:4',
        '    1: (18, [6, 10, 14]),  # _continue_script: + post_script:4',
        '    2: (18, [6, 10, 14]),  # _double: + not_enough_pkmn:4',
        '    3: (10, [6]),  # _rematch: lose:4 only? verify',
        '    4: (14, [6, 10]),  # _rematch_double',
        '    5: (18, [6, 10, 14]),  # _continue_script_double',
        '    6: (18, [6, 10, 14]),  # _earlyrival',
        '    7: (10, [6]),  # _no_intro: only lose_text',
        '    8: (14, [6, 10]),',
        '    9: (14, [6, 10]),',
        '}',
    ])
    out_path.write_text("\n".join(lines) + "\n")
    print(f"Wrote {out_path} with {len(opcodes)} opcodes")


if __name__ == "__main__":
    main()
