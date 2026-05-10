# 2024 ROM font location — open question

**Status (2026-05-10, late):** still unresolved, but the static path is now
exhausted — the font is **not** stored as a single LZ77 block, and **not**
in any code area we can statically locate from the call graph.
See "Update 2026-05-10 (capstone disassembly attack)" below.

**Earlier status:** Coverage capped at 81.3% (539/~1000 codepoints).

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

## Update 2026-05-10 (capstone disassembly attack)

Without Ghidra, we used capstone (Thumb mode) to do equivalent static
analysis. New tools in this dir:

- `find_lz77_sites.py` — every Thumb `SVC #0x12` / `#0x11` instruction in
  the ROM, with disassembly context. Note: Thumb halfwords are LE, so SVC
  imm bytes are `[imm, 0xDF]` not `[0xDF, imm]` (a previous brute-force
  search had this reversed).
- `find_lz77_callers.py` — locates the BIOS LZ77 wrappers (`LZ77UnCompVram`
  @ 0x081e3bb8 and `LZ77UnCompWram` @ 0x081e3bbc) by byte signature
  (`12 df 70 47`), then scans for every Thumb `BL` whose 22-bit signed
  offset resolves to one of those wrappers. For each caller, walks back
  ~80 instructions and resolves the most recent `LDR Rd, [PC, #imm]` into
  r0 (compressed source) and r1 (destination) via literal-pool
  arithmetic. Output: `lz77_callers_2024.json`.
- `inspect_lz77_candidates.py` — pure-Python GBA LZ77 type-0x10
  decompressor. Dumps each candidate's uncompressed bytes plus tile
  density / variance.
- `scan_patched_lz77.py` — brute-force every `byte == 0x10` in the
  patched region (0xD00000..0xFFFFFF), attempt LZ77 decompress, score
  for "looks like hangul tile data" (mid density, high variance, glyph
  pair-match ratio). Output: `patched_lz77_blocks.csv`.
- `render_lz77_candidates.py` — render any candidate as a tile-grid PNG
  (8x8, 16x8, 16x16 layouts) for visual inspection. Outputs in
  `lz77_renders/`.
- `diff_vanilla.py` — byte-diff the 2024 Korean ROM against the vanilla
  Japanese base (`1362 - Pokemon Leaf Green (J)(Cezar).gba`,
  md5 138a71a5be83f3f3d7af3d31916a5fc7). Output: `diff_runs_2024.txt`.

### Findings

1. The 2024 Korean patch does *massive* in-place rewrites of the vanilla
   code/data region. Top patches:
   - rank 1: file 0x5613c4..0x717700 (1.79 MB) — bulk text/script data
   - rank 2: file 0x4b7c1b..0x5613bb (694 KB) — more data
   - rank 3: file 0x6ccd2..0xb2e68 (287 KB) — **contains the rewritten
     text engine**, including the 0x9f850 BL site we identified
   - rank 4: file 0xdc1fc..0x120089 (278 KB) — also code/data
   - rank 16: file 0xc432c..0xdc1ee (98 KB) — more code

2. **No new code in the patched region** (≥ 0xD00000). All the SVC `#0x12`
   bytes there fail the "coherent Thumb context" check (capstone produces
   ARMv7-T2 instructions like `mcr2 p5, ...` and `vhadd.u8` that the GBA
   ARM7TDMI cannot run). And there are zero `BL` instructions in vanilla
   code that target the patched region. So the rewritten text engine
   lives entirely inside vanilla code addresses; the patched region is
   data only.

3. **The font is not stored as an LZ77 block**, or at least not via any
   path we can find statically. We located 15 BL-callers of LZ77 wrappers
   that have a source pointer in the patched region. After decompressing
   and rendering all 15:
   - 0x8e98164 → 1.5 KB icons (UI/Pokémon Center)
   - 0x8e9b464, 0x8e9b52c → ~384 B each, dialog textbox borders
   - 0x8e9cb60 → 528 B tilemap
   - 0x8eb0e24 → 200 B tilemap
   - 0x8eb8854 → 1024 B sprite
   - The remaining 8KB-class blocks elsewhere in the patched region are
     vanilla Japanese assets (battle UI, contest portraits, kana text)
     that the patch left untouched but which still appear in the bulk
     diff because they got moved/copied.

4. **The font must be uncompressed**, somewhere in the patched data region,
   and the rewritten renderer dereferences it directly via a literal-pool
   pointer that we have not yet identified. Candidates: 151 unique
   patched-region pointers in rank-3, 382 in rank-4, etc. (see
   `find_lz77_callers.py` style sweep but for plain u32 reads).

### Recommended next step

Switch to **runtime tracing via mGBA's GDB stub** (the original suggestion
#2). `tools/moneo/gdb_client.py` already speaks the protocol. Procedure:

1. Boot the 2024 ROM in `mgba -g leafgreen_J-K_2024.gba`.
2. Drive the game past the title screen until Korean text is on screen
   (a save state with text mid-render is ideal).
3. Use the GDB client to dump VRAM 0x06000000..0x06010000 and search
   the ROM file for matching tile bytes — the offset is font_base.
4. Or set HW execution breakpoints on every BL into a glyph-copy
   helper (the rewritten function inside rank-3 region) and capture
   r0/r1/r2 for each glyph render, which directly gives the font_base
   + per-glyph offset.

Code regions inside the rewritten text engine (rank 3) likely contain
the per-glyph rendering function. The most-referenced patched-region
pointers from there — `0x8eae3dc`, `0x8ead7bc`, `0x8ece486`,
`0x8ecb1d6` — are leading candidates for either font_base or the
codepoint-→-glyph translation table.
