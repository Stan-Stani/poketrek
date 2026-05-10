# 2024 ROM font location — open question

**Status (2026-05-10):** unresolved. Coverage capped at 81.3% (539/~1000 codepoints).

## What we know

- The 2024 patch encodes dialog and name tables as 16-bit big-endian
  codepoints in the range `0x3700..0x40FF` (~2560 possible slots,
  ~1000 actual syllables).
- The codepoint→syllable map at `codepoint_map.json` was built by
  triangulating against PokeAPI Korean move/ability/species names
  (`build_codepoint_map.py` + `iterative_resolve.py`). Maxed out at 533
  entries because canonical name tables don't cover the full vocabulary.
- A 6th iteration via `tools/moneo/triangulate_codepoints.py` (n-gram
  scoring against the 2010 corpus) yielded 5 additional manually-verified
  labels: 했, 않, 졌, 듯, 있. Net 539. Most other suggestions were
  ambiguous or wrong on inspection.
- The patched-content region of the 2024 ROM is `0xD00000..0xFFFFFF`
  (3MB; original FRLG ends at `0x800000`). The Korean font tile data
  almost certainly lives in this region.

## Approaches that did NOT work

### Brute-force codepoint→pointer table search
Tried every 4-byte-aligned base offset that satisfies:
- `*(base + cp*4)` for cps `0x3701..0x3703` are sequential ROM pointers
- Pointers spaced by 32/64/96/128/256 bytes
- Pointers for the gap codepoints `0x3704..0x3707` are constant (a
  single "blank" tile)
- Targets land in patched region (`>= 0xD00000`)
- Glyph-byte data at the targets passes a "looks like a tile" filter
  (mid-density, varies between adjacent codepoints)

Result: **0 hits**. The codepoint→font map is not a simple flat u32
pointer table; it's some other structure.

### Brute-force flat-byte font search
Tried `font_base + (cp - 0x3700) * stride` and `font_base + cp * stride`
for stride in `{32, 64, 96, 128, 160, 256}`, requiring:
- Glyph for `0x3701` (가) is non-zero, glyph-like
- Glyphs for `0x3704..0x3707` are blank
- Adjacent mapped cps share top-half bytes (가/각/간 share initial+vowel)

Got 38 candidates with stride=128 at the strictest setting. Visual
rendering of the candidates as 4bpp 16x16 / 1bpp 16x16 / linear-row-major
showed stripe-y noise patterns, not real hangul. The constraint matches
were coincidental.

### Literal-pool hunt for `0x3700`
Scanned for u32 LE `0x00003700` (which would be loaded by an
`LDR Rn, [PC, #imm]` in the rendering function's literal pool). Found
3 hits: `0x26E568`, `0xD215E8`, `0xEA2660`. Disassembly via capstone of
the surrounding `0x100` bytes produced incoherent Thumb instructions —
the hits are inside data regions, not code.

## Likely actual encoding

Strong hypotheses for why brute force fails:
- **LZ77 compression.** Pokefirered uses LZ77-compressed sprites/fonts
  via `RsFastLZ77UnCompTextWindowGraphicsBuffer` and SWI 0x12. The
  Korean patch may store the font as one (or a few) LZ77-compressed
  blocks that get unpacked to VRAM at runtime. A font_base search
  against the compressed bytes won't match on per-glyph stride.
- **Multi-step indirection.** Original pokefirered uses
  `gFontShortGlyphsXTable` (multiple per-page tables, each with
  pointer + width arrays). The Korean patch may have its own
  per-page tables indexed by `(cp >> 8) - 0x37`.
- **Variable-width glyph descriptors.** A struct of
  `{tile_ptr: u32, width: u8, ...}` with non-32-byte stride would
  defeat the simple pointer-table search.

## Recommended next steps

1. **Use a real disassembler.** Load `leafgreen_J-K_2024.gba` into
   Ghidra (free) or IDA. The rendering function patches the original
   FRLG `DecompressGlyph_Normal` (in pokefirered, `text.c:1430`).
   Find the new function in the patched region and follow the LDRs
   from its literal pool. The font_base should be one of those LDRs.
2. **Use mGBA's debugger.** With a save state mid-dialog, set a
   memory-read breakpoint on VRAM tile-load addresses and step out
   to the calling function. The PC at break shows the renderer.
3. **Diff against vanilla Japanese FRLG 1.0.** The 2024 patch is
   xdelta'd over the Japanese ROM (md5
   `138a71a5be83f3f3d7af3d31916a5fc7`). A binary diff highlights
   exactly which functions were replaced — narrows the search to the
   patched code regions.

## Disassembly attempt findings (2026-05-10)

Found a structured resource table at `0x3AD000` (502 entries, 8 bytes
each: `{u32 ptr, u32 meta_id_or_flags}`). Each entry's pointer targets
an LZ77-compressed block in the patched region. Confirmed by header
byte `0x10` plus reasonable uncompressed size in bytes 1-3.

Decompression works (GBA-standard LZ77, type 0x10). Sample of
8192-byte uncompressed blocks (the largest entries — candidates for
font pages):
- `0xD25DC0`, `0xD2B230`, `0xE7C008` — all decompress to all-0xFF
  tiles. These are palette/tilemap/window-graphics data, not glyphs.
- `0xD1C9BC` — decompresses to abstract shape tiles (mostly all-fill
  or all-blank). Sprite data, not hangul.

So **the resource table at 0x3AD000 is for general game graphics, not
specifically the hangul font**. The font is stored elsewhere — likely
either:
- An uncompressed flat array at a yet-unfound offset, indexed by some
  codepoint-decomposition function we haven't reverse-engineered, or
- Compressed in chunks at offsets reachable only by the rendering
  function's literal pool.

Capstone disassembly of code regions around the few literal-pool
references to `0x00003700` failed to produce coherent Thumb code —
the "literal pool entries" turned out to be inside data tables.

Real progress here requires either Ghidra/IDA (interactive disassembly
with cross-references) or runtime trace from mGBA's debugger.

## Files in this directory

- `apply_patch.py` — applies the 2024 xdelta to base Japanese FRLG
- `find_offsets_2024.py` — re-derives gMapGroups / gItems / etc.
- `find_name_tables.py` / `decode_name_tables.py` — name-table
  extraction (which got us the 533-codepoint seed)
- `build_codepoint_map.py` / `iterative_resolve.py` — PokeAPI
  triangulation pipeline
- `codepoint_map.json` — current map (539 entries)

The dialog corpus rebuild at the parent level
(`tools/moneo/scan_rom_2024.py`) is unblocked and works fine at the
current coverage. Extending to ~95% requires the disassembly route.
