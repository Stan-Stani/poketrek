# Korean LeafGreen Text Engine — Disassembly & Findings

This document captures the static reverse-engineering of the Korean LeafGreen
text engine, performed against ROM `Pocket Monsters - LeafGreen (Korean).gba`.

## Engine entry: 0x08384800

`pre_byte_handler` — runs once per text byte. Stores the page byte
(0xF1..0xF6 → 1..6) at IWRAM `0x03007E3F`, advances the string pointer by 2
on Korean tokens, and tail-jumps to the main text engine.

```
push {r5, r6}
ldr  r1, =0x03007E3F        ; page-byte mailbox
movs r3, #0
strb r3, [r1]               ; default page = 0
ldr  r0, [r6]               ; r6 = pointer-to-pointer (string ptr cell)
ldrb r3, [r0]               ; current byte
cmp  r3, #0xF0
bls  .return                ; <= 0xF0: not a Korean syllable; defer
cmp  r3, #0xF7
bhs  .return                ; >= 0xF7: control byte; defer
subs r3, #0xF0              ; r3 = 1..6
strb r3, [r1]               ; store page
ldrb r3, [r0, #1]           ; idx byte (consumed implicitly via state)
adds r0, #2                 ; advance ptr by 2
str  r0, [r6]
ldr  r0, =0x08005ACC        ; main text engine
mov  pc, r0                 ; tail-jump (Thumb mode)
.return:
bx lr
```

### Literal pool at 0x08384920

| Addr        | Value        | Meaning                                    |
| ----------- | ------------ | ------------------------------------------ |
| 0x08384920  | 0x03007E3F   | IWRAM page-byte mailbox                    |
| 0x08384924  | 0x08005ACC   | Main text engine entry                     |
| 0x08384928  | 0x0838492C   | Pointer to font-pointer table              |
| 0x0838492C  | 0x081DEEE8   | Font ptr [0]: non-Korean base font         |
| 0x08384930  | 0x08780000   | Font ptr [1]: Korean page F1               |
| 0x08384934  | 0x08784000   | Font ptr [2]: F2                           |
| 0x08384938  | 0x08788000   | Font ptr [3]: F3                           |
| 0x0838493C  | 0x0878C000   | Font ptr [4]: F4                           |
| 0x08384940  | 0x08790000   | Font ptr [5]: F5                           |
| 0x08384944  | 0x08794000   | Font ptr [6]: F6                           |
| 0x08384948  | 0x08798000   | Font ptr [7]: extended                     |
| 0x08384950  | 0x081CEDD0   | (referenced)                               |

### Font-pointer lookup helper at 0x083848D8

Reads the page byte from `0x03007E3F`, multiplies by 4, indexes into the
font-pointer table at `0x0838492C`, returns `r1 += font_page_base[page]`.
**This is purely a font-data fetcher; there is no (page,idx) → glyph-id
translation table.** The text-token (page, idx) is consumed directly as the
addressing scheme for glyph pixel data.

## Main engine: 0x08005ACC (Thumb)

State-machine dispatcher with table at 0x08005AE0. States 0..1 → glyph render
at 0x080062B4, states 2..5 → control-char render at 0x080064B8.

The glyph render function at 0x080062B4 packs (page, idx) into r0 bits and
calls a font-page fetcher via the trampoline at 0x0839372A → 0x083848D8
described above.

## Conclusion: there is no in-ROM (page, idx) → ksx1001 LUT

The text engine's only "translation" is page-byte → font-base-address. The
glyph data in font pages F1–F6 is the source of truth for what each (page,
idx) renders. To map (page, idx) → Hangul one must either:

1. Visually identify each glyph (manual labeling or reliable OCR), or
2. Trace the live emulator and pair each ROM token with the resulting VRAM
   fingerprint (Path 2 in newPlan.md).

## Glyph data format (verified visually)

- 6 ROM pages × 0x4000 bytes from 0x780000.
- Each page is a 16-glyph-wide × 32-row grid of 16×16 px glyphs at 2bpp.
- Glyph byte offset within page: `0x200 * (slot // 16) + 0x20 * (slot % 16)`.
- Sub-tile order within glyph: TL @ +0, TR @ +16, BL @ +256, BR @ +272.
- Each 8×8 sub-tile is 16 bytes 2bpp with the v8 byte-swap convention:
  byte at +1 = left 4 px, byte at +0 = right 4 px, MSB = leftmost pixel.
- Total addressable slots: 6 × 512 = 3072. Empirical non-blank count ≈ 3010.

## VRAM fingerprint mystery (unresolved)

The 45 verified (fingerprint → Hangul) entries in
`app/src/main/assets/moneo/ko_charmap.json` could **not** be matched by any
combination of:

- Sub-tile order (4! permutations)
- 2bpp byte ordering (LSB/MSB-first, byte-swapped or not)
- 4bpp nibble packing (low or high first)
- Palette value-map permutations on values 0..3
- Pair compositions of (top half, bottom half) ROM glyphs across all 2,968
  candidate 16×8 slots

Plain-byte sliding-window search for any 128-byte sequence in ROM hashing
to one of the fingerprints also returned **zero matches**.

This implies the live VRAM data either (a) goes through a non-trivial
runtime transformation (e.g. shadow compositing, palette-bank biasing, or
combination with a separate font), or (b) is sourced from a font region we
haven't located. Path 2 (live mGBA GDB trace) remains the realistic way to
resolve this.
