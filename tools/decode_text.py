#!/usr/bin/env python3
"""
decode_text.py — Decode raw ROM text records using glyph-table.json.

Reads .moneo-artifacts/rom-text-ko-raw.json and produces:
  - decoded-text.json (all records with translated text)
  - decoded-text.txt (human-readable dump, only Korean records)
"""
import os
import sys
import json

ART = ".moneo-artifacts"

# Single-byte controls (Korean ROM uses page-byte tokens for actual chars,
# so we deliberately do NOT use the FRLG English charmap — those bytes mean
# something else here, mostly tile indices for non-Hangul UI glyphs).
SINGLE = {0xFA: '\n', 0xFB: '\n\n', 0xFE: '\n', 0xFF: '',
          0xAB: '!', 0xAD: '.'}


def load_glyph_table(path):
    with open(path, encoding='utf-8') as f:
        raw = json.load(f)
    table = {}
    for k, v in raw.items():
        # k = "F<page>,<idx>"; v = char or {"char": ..., "conf": ...}
        page_str, idx_str = k.split(',')
        page = int(page_str[1:])
        idx = int(idx_str)
        if isinstance(v, dict):
            v = v.get('char')
        if v:
            table[(page, idx)] = v
    return table


def decode_record(rec, glyph_table):
    out = []
    for tok in rec.get('tokens', []):
        k = tok['k']
        v = tok['v']
        if k == 'P':
            page_byte, idx = v[0], v[1]
            page_num = page_byte - 0xF0  # 1..6 valid; 7..12 are mis-tokenized controls
            if page_num >= 7:
                # Mis-parsed: bytes F7..FC are controls, not page selectors.
                # Treat first byte as control, second as next char.
                if page_byte == 0xFA:
                    out.append('\n')
                elif page_byte == 0xFB:
                    out.append('\n\n')
                elif page_byte == 0xFC:
                    pass  # color/format (1+param byte) - swallow both
                else:
                    out.append(f'⟨{page_byte:02X}⟩')
                # We already consumed both bytes; can't recover the second.
                continue
            ch = glyph_table.get((page_num, idx))
            out.append(ch if ch else f'⟨F{page_num}:{idx:02X}⟩')
        elif k == 'X':
            b0, b1 = v[0], v[1]
            if b0 == 0xFD:
                out.append(f'⟨var:{b1:02X}⟩')
            elif b0 == 0xFC:
                pass  # format command
            else:
                out.append(f'⟨{b0:02X}{b1:02X}⟩')
        elif k == '?':
            ch = SINGLE.get(v)
            if ch is not None:
                out.append(ch)
            # else: skip unknown single byte
    return ''.join(out)


def main():
    table_path = os.path.join(ART, 'glyph-table.json')
    raw_path = os.path.join(ART, 'rom-text-ko-raw.json')

    glyph_table = load_glyph_table(table_path)
    print(f"Loaded {len(glyph_table)} glyph mappings")

    with open(raw_path, encoding='utf-8') as f:
        raw = json.load(f)
    records = raw['records']
    print(f"Decoding {len(records)} records...")

    decoded = []
    for rec in records:
        text = decode_record(rec, glyph_table)
        decoded.append({
            'offset': rec['offset'],
            'len': rec['len'],
            'text': text,
        })

    # Stats
    has_ko = [d for d in decoded if any('\uAC00' <= c <= '\uD7A3' for c in d['text'])]
    fully_decoded = [d for d in decoded if '⟨F' not in d['text']
                     and any('\uAC00' <= c <= '\uD7A3' for c in d['text'])]
    print(f"Records with Korean: {len(has_ko)}")
    print(f"Fully decoded:       {len(fully_decoded)}")

    # Pure-Korean filter: records where ≥70% of tokens are Korean syllable pairs
    def ko_purity(rec):
        toks = rec.get('tokens', [])
        if not toks:
            return 0
        return sum(1 for t in toks
                   if t['k'] == 'P' and 0xF1 <= t['v'][0] <= 0xF6) / len(toks)

    pure_idx = {i for i, r in enumerate(records) if ko_purity(r) > 0.7
                and len(r.get('tokens', [])) > 3}
    pure = [d for i, d in enumerate(decoded) if i in pure_idx]
    print(f"Pure-Korean (>=70% syllable tokens, >3 tokens): {len(pure)}")

    # Save
    json_path = os.path.join(ART, 'decoded-text.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(decoded, f, ensure_ascii=False, indent=2)
    print(f"Wrote {json_path}")

    txt_path = os.path.join(ART, 'decoded-text.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        for d in decoded:
            if any('\uAC00' <= c <= '\uD7A3' for c in d['text']):
                f.write(f"[0x{d['offset']:06X}] {d['text']}\n\n")
    print(f"Wrote {txt_path}")

    pure_path = os.path.join(ART, 'decoded-text-pure.txt')
    with open(pure_path, 'w', encoding='utf-8') as f:
        for d in pure:
            f.write(f"[0x{d['offset']:06X}] {d['text']}\n\n")
    print(f"Wrote {pure_path}")

    # Print samples — fully decoded ones first (most readable)
    print("\n──── Fully decoded samples ────")
    for d in fully_decoded[:10]:
        print(f"  0x{d['offset']:06X}: {d['text']!r}")

    print("\n──── Sample with unknown glyphs ────")
    partial = [d for d in has_ko if d not in fully_decoded][:10]
    for d in partial:
        print(f"  0x{d['offset']:06X}: {d['text']!r}")


if __name__ == '__main__':
    main()
