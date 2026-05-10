# 2024 ROM font location — RESOLVED

**Status (2026-05-10, end-of-day):** font_base, dispatcher, row blitter,
and decoder all identified via runtime single-step tracing (no Ghidra
needed). See "Update 2026-05-10 (single-step trace)" at bottom for the
live findings. Earlier sections record the dead-end paths.

**Quick reference:**

| Component | Address (GBA) | File offset | Notes |
|-----------|---------------|-------------|-------|
| Glyph atlas 0 (font_base) | `0x08edf800` | `0xedf800` | 64-byte stride per glyph; only first 32 bytes used |
| Width table 0 | `0x08f17800` | `0xf17800` | u8 per glyph |
| Glyph atlas 1 | `0x08f18800` | `0xf18800` | second hangul atlas (different style) |
| Width table 1 | `0x08f50800` | `0xf50800` | |
| Glyph atlas 2 | `0x08f51800` | `0xf51800` | third hangul atlas |
| Width table 2 | `0x08f89800` | `0xf89800` | |
| Composer / dispatcher entry | `0x080057a4` | `0x57a4` | reads `[r6+0x1c]` mode byte → 7-way jump table |
| Row blitter (cache writer) | `0x08003028` | `0x3028` | per-pixel 4bpp OR-merge into EWRAM `0x02007800..0x02009000` |
| Glyph decoder (LUT-driven) | `0x08002fa0` | `0x2fa0` | byte → ROM LUT @ `0x081ea090` → IWRAM LUT @ `0x03000a40` (populated at boot) |
| Per-handler call sites | `0x800645c`, `0x8006504`, `0x80065cc`, `0x8006738`, `0x8006800`, `0x800696c` | | 6 jamo / mode handlers; each loads `font_base + cp*64` |
| Glyph cache (EWRAM staging) | `0x02007800..0x02009000` | — | the 4bpp composition buffer |
| IWRAM glyph staging | `0x03003da0` | — | between decoder and row blitter |

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

## Update 2026-05-10 (runtime VRAM trace, partial)

Stood up the runtime trace path. Tooling now in this dir:

- `dump_vram.lua` — mGBA Lua script that holds START/A through the
  GameFreak intro and dumps VRAM/EWRAM/palette/OAM to /tmp at a
  configurable frame. Run with `mgba --script dump_vram.lua leafgreen_J-K_2024.gba`.
  Confirmed working: 96 KB VRAM + 256 KB EWRAM + palette + OAM all
  pulled in under a second of script time. The Qt mGBA's GDB stub
  (`-g`) does not survive a single connect/disconnect cycle on macOS,
  so Lua is the supported path here.
- `find_font_via_vram.py` — searches ROM for byte-for-byte 32-byte
  4bpp VRAM tiles. Returned 0 hits → font is not stored in 4bpp.
- `find_font_via_vram_1bpp.py` / `find_font_encoding.py` — encoders for
  1bpp forward, 1bpp bit-reversed, 2bpp linear, 2bpp Game-Boy-style.
  1bpp_rev gave 27 unique-tile hits in the patched region; the others
  ≤ 16. None produced a stride run (consecutive VRAM tile → consecutive
  ROM offset), and on inspection the apparent dense cluster around
  ROM 0xe9c000 was repetitive low-entropy data that random-matches
  many tile signatures by coincidence.

### What we learned

The dump was taken on the **title screen**, where the visible Korean
text is the stylized "리프그린버전" *logo* — that's custom sprite
artwork, not the dialog font. Searching for it byte-wise in ROM finds
its source in pre-rendered form, but reveals nothing about the dialog
font (which is what we need for codepoint→glyph mapping). The dialog
font only appears when the engine actually renders text via
`DecompressGlyph_*` — i.e., at the New-Game / Continue menu, or in
Professor Oak's intro dialog.

### Concrete unblocker for next session

Capture VRAM at a screen that uses the **dialog font**. Two ways:

1. (Easiest) Manually drive the 2024 ROM in mGBA past the title until
   the New Game / Continue menu is visible. Save state. Save the
   `.ss0` file alongside the ROM, named e.g. `2024_dialog.ss0`. Then
   modify `dump_vram.lua` to `emu:loadStateFile("2024_dialog.ss0")`
   on first frame and dump immediately. The VRAM tiles for menu
   labels will be byte-identical to font bytes in ROM, give or take
   one of the encodings already enumerated in `find_font_encoding.py`.

2. Extend `dump_vram.lua` to keep stepping past START → past
   "PRESS START" → into the menu, and dump VRAM at each of those
   frames. The first time the dialog font appears, encoding-search
   will land us on font_base.

The existing 5 save states (`*.ss0` under repo root) appear to be from
the **2010** Korean ROM, not the 2024 ROM — different ROM, save states
are not portable. So a fresh save state is needed.

## Update 2026-05-10 (drove the game to a dialog screen)

Stopped depending on save states. New tool `drive_to_dialog.lua` scripts
input directly: holds A/START past the GameFreak intro, the title screen,
and into Professor Oak's "Welcome to the Pokémon world" intro speech.
Snapshots VRAM/EWRAM/palette + a PNG screenshot every 30 frames, into
`/tmp/poketrek_drive/`. Snapshots 010 (frame 630) through 014 (frame 750)
all show full dialog text on screen.

### Result of byte-search against the dialog VRAM

Every encoding still fails to produce a stride run:

- **4bpp (raw 32-byte VRAM tile)** — 1 unique patched-region match.
- **1bpp_fwd** — 38 patched matches, top 4KB bucket = 0xe9d000 (18).
- **1bpp_rev** — 37 patched matches, top 4KB bucket = 0xe9d000 (19).
- **2bpp linear / GB-style** — fewer than 6 each.

When restricted to "VRAM tiles that *just appeared* between frame 570
and 630" (i.e., literally the dialog tiles), the top buckets shift to
the vanilla ROM region: 0x476000 (19 hits, 1bpp_fwd), 0x4a0000–0x522000.
But rendering those regions as 1bpp shows high-density noise, not
glyphs. No encoding produces a clean stride run; the apparent buckets
are statistical artifacts of common 8-byte patterns in dense data.

A separate angle — searching for verbatim ROM-byte chunks inside the
dialog-frame **EWRAM** dump — found a 9-element stride run at
EWRAM 0x37218..0x37258 ↔ ROM 0x45db90..0x45dbd0 (8B stride,
byte-for-byte). The ROM bytes there *are* patched (94.6% differ from
vanilla in the surrounding 12 KB), but rendering the bytes as 1bpp,
2bpp, or 4bpp produces noise — they are *not* glyph bitmaps. The
match is real but the bytes are some other rewritten data structure
(state, table, or compressed payload) that happens to be copied to
EWRAM at boot.

### Working hypothesis: jamo-decomposed rendering

Hangul has structural decomposition: every syllable is 2 or 3 *jamo*
(initial consonant + medial vowel + optional final consonant). The
canonical engineering approach for a Korean GBA font in a
storage-constrained ROM hack is to store ~70 jamo bitmaps and
compose syllable glyphs at runtime. That would explain why no single
VRAM 16x16 glyph byte-matches anywhere in the ROM in any pixel format:
the bytes in VRAM are the **OR of 2–3 source bitmaps**, none of
which appears intact at any ROM offset.

Confirming this requires runtime instrumentation that either
(a) breaks on writes to a specific dialog-tile VRAM address and
captures the source pointer at the time of the write, or (b) traces
the rewritten renderer (the rank-3 patch at file 0x6ccd2..0xb2e68
contains it) instruction-by-instruction.

mGBA's Qt GDB stub on macOS won't survive a single
connect/disconnect, but the Lua API exposes `emu.memory.<region>:set8`
hooks that can serve as runtime watches. Continuing this hunt is
worthwhile **only** if ~95%+ codepoint coverage is needed — current
coverage at 81% supports the dialog corpus rebuild adequately.

## Update 2026-05-10 (jamo decomposition CONFIRMED)

The jamo-decomposition hypothesis is now empirically verified.

**Where:** EWRAM 0x02007000..0x02009000 (= dump offset 0x7000..0x9000).
This is the rendered-glyph cache where the renderer lays out 4bpp 8x8
tiles before they get DMA'd to VRAM.

**Palette:** {0, 2, 3}. Index 0 = transparent. Indices 2 and 3 are two
distinct foreground colors used per-tile.

**Decomposition test** (`extract_jamo_layers.py`):
- 146 two-color glyph-cache tiles examined.
- Shadow-shift hypothesis (color 2 = color 3 shifted): only 5/146
  match `shift(m3, -1, 0)`, no other shift hits more than 1.
- Containment: `m2 ⊆ m3` and `m3 ⊆ m2` both = 0/146.
- → Color 2 and color 3 are **independent layers**. Not a glyph + its
  shadow, but two separate jamo bitmaps composited into the same cell.

**Visual confirmation** (`jamo_color2_layer.png`, `jamo_color3_layer.png`):
each layer in isolation shows clean hangul jamo strokes — verticals
(ㅣ), horizontals (ㅡ), small squares (ㅁ), and consonant shapes
(ㄴ, ㄹ, ㅂ, ㄷ). Combined (`jamo_combined.png`) reproduces the
visible dialog-frame syllables.

### What we still don't have

Searching the ROM byte-for-byte for these layer masks (1bpp_fwd /
1bpp_rev / 4bpp-equivalent / 2bpp / column-major / horizontal-doubled)
returns no real font_base. Some buckets at 0x476800, 0x4b9400, 0x4f0400
have several "matches", but inspecting them shows the hits are all the
trivial mask `0101010100000000` (4 pixels at left edge) hitting against
incidental tilemap data. No real jamo source has been located by static
byte search.

The jamo bitmaps are stored in the patched ROM in some encoded form
the static search hasn't covered:
- Bit-packed at sub-byte granularity (each jamo using `n` bits, not
  multiples of 8)
- Run-length / stroke-encoded (the renderer interprets stroke
  primitives, not pixel data)
- Indirect through a small table that the renderer addresses via a
  decomposed-codepoint formula (initial_idx, medial_idx, final_idx
  are computed from the BE codepoint)

### Recommended next attack

Inspect the rewritten renderer in vanilla code at file 0x9f850 (the BL
LZ77UnCompWram site we located statically). Read backward from there to
find the dispatch function that fetches a jamo bitmap given a
codepoint. The literal pool of THAT function points at the jamo
storage. Capstone can do this; the rank-3 patch contains the code; the
167 + 382 patched-region pointers found earlier in `find_lz77_callers.py`
output cover most of the candidates.

## Update 2026-05-10 (composer search narrowed, jamo atlas not yet)

`find_glyph_composer.py` scanned all rewritten code for u32 literals
in the EWRAM glyph-cache range 0x02007000..0x02009000. Findings:

- 151 such literals across the rewritten regions, 50 distinct values.
- The most-referenced cache addresses are: `0x02007890` (24×),
  `0x020078d0` (11×), `0x02007888` (10×), `0x02007808` (8×),
  `0x02007880` (8×), `0x02007800` (7×), `0x02007990` (7×).
  These are specific glyph-tile slots (each 16-byte stride apart).
- A function array at file `0xc79ac..0xc9528` (rank-16 patch) contains
  the EWRAM→VRAM DMA helpers — multiple ~0x54-byte functions, each
  loads `0x02007890` and `0x06007910` (VRAM target) and copies tile
  bytes from cache to display.
- Function at file `0x11a966` (rank-4 patch) is a text-format helper:
  reads bytes from a script struct, calls `bl 0x8d98` (probably
  `strcpy`-style) with src in patched ROM (0x8edd5c0, etc.) → looks
  like localized format strings, not glyph data.
- Function at file `0x11a494` is a 7-way jump table that sets text
  formatting flags (color/font/alignment).
- Searches for u32 literal `0x3700` / `0x3701` / `0x40FF` (codepoint
  range constants): **0 hits** in the rewritten code. The composer
  uses immediate-value arithmetic for codepoint decomposition rather
  than a literal-pool constant, which leaves no fingerprint to search.

**Bottom line:** the path to the jamo atlas requires interactive
disassembly (Ghidra/IDA). Capstone-based static analysis has
fingerprinted the surrounding text-engine machinery (DMA helpers,
formatters, jump tables) but the codepoint-decomposition logic
itself uses arithmetic that doesn't surface in the literal pool, and
the actual jamo bitmap data has resisted every byte-pattern search
under every encoding tried.

Continuing past 81% codepoint coverage on this ROM is firmly in the
"diminishing returns vs. effort" zone. The codepoints we have
support the dialog corpus rebuild; the unknowns are concentrated
in low-frequency syllables that triangulation doesn't reach.

### Files added in this update

- `find_glyph_composer.py` — scans for EWRAM-glyph-cache literals
  in the rewritten code regions, lists candidate composer anchors
  with their nearby patched-ROM literals.
- `extract_jamo_layers.py` — empirically verifies the jamo
  decomposition hypothesis from the EWRAM glyph cache.

## Update 2026-05-10 (call-graph walk; engine task system identified)

`walk_call_graph.py` — minimal Ghidra-substitute. Given a file offset,
it (a) finds the nearest preceding `push {... lr}` that's a coherent
function start, (b) walks forward to the matching `pop {... pc}` /
`bx lr`, (c) collects every BL caller of that function, (d) finds
function-pointer references in u32 literals (Thumb LSB convention),
and (e) recursively walks up the call chain.

Walking from the BL LZ77UnCompWram site at file 0x9f850:

```
FUNC 0x9f844..0xa0844  (the LZ77 caller — loads icon graphics 0x8e98164)
  callers: 1 BL  →  installed via callback at 0x9d9a0
FUNC 0x9d23c..0x9d9ae  (the parent state handler)
  → uses `bl 0x558` to install the next-state callback
FUNC 0x558..0x568  ; ldr r1, [pc, #c]; str r0, [r1, #4]; bx lr
  ; this is `SetTaskFunc(slot, fn)` — pokefirered's task system
```

So the "callback installation" pattern (`bl 0x558`) is the **engine-wide
task scheduler**, not specific to text rendering. We found **127 unique
task handlers** installed this way across the ROM. That's the entire
game's task system, far too broad to be useful as a discriminator.

### Where the search stops

The font hunt is now blocked on something static analysis can't answer
in reasonable time without an interactive disassembler:

- The composer's codepoint decomposition uses immediate arithmetic
  (no literal-pool fingerprint).
- The jamo bitmap encoding is non-trivial (no byte pattern matches at
  any 1bpp/2bpp/4bpp interpretation).
- The renderer is woven into the engine task system, so its callers
  aren't directly identifiable from BL site analysis alone.
- The glyph cache at EWRAM 0x02007800..0x02009000 is the proven
  composition target, but the function(s) that *write* into it are
  hidden behind multi-step task-handler chains.

What's needed to unblock: load the ROM into Ghidra (or IDA Free), set
0x9f844 as the entry point, and use cross-references to walk up the
graph interactively. With Ghidra one can also identify the codepoint
decomposition by its arithmetic fingerprint (constant divisors of
21*28 = 588 and 28, characteristic of Korean syllable indexing).

### Files added in this update

- `walk_call_graph.py` — recursive call-graph walker for capstone
  (handles BL callers + function-pointer table refs).

### Files added in this session

- `find_lz77_sites.py`        — capstone scan of every Thumb SVC #0x12/0x11
- `find_lz77_callers.py`      — every BL caller of the BIOS LZ77 wrappers, with literal-pool resolution
- `inspect_lz77_candidates.py`— pure-Python GBA LZ77 type-0x10 decompressor
- `scan_patched_lz77.py`      — every LZ77 block in the patched region, scored for tile-likeness
- `render_lz77_candidates.py` — render any LZ77 block as 8x8/16x8/16x16 PNG
- `diff_vanilla.py`           — byte-diff 2024 ROM vs vanilla Japanese FRLG
- `dump_vram.lua`             — mGBA Lua: dump VRAM/EWRAM/palette/OAM at frame N
- `drive_to_dialog.lua`       — mGBA Lua: scripts START/A inputs past intro+title into Oak's dialog, snapshots every 30 frames
- `find_font_via_vram.py` / `_1bpp.py` / `find_font_encoding.py` — per-encoding signature search

Generated artifacts (gitignored): `lz77_callers_2024.json`,
`lz77_sites_2024.json`, `patched_lz77_blocks.csv`,
`diff_runs_2024.txt`, `lz77_candidates_2024/`, `lz77_renders/`.

## Update 2026-05-10 (single-step trace — RESOLVED)

The earlier static-analysis path correctly identified that the composer
uses immediate-value arithmetic with no literal-pool fingerprint, so
the byte-pattern hunt had no anchor. Switching to **runtime single-step
tracing** with mGBA's Lua scripting (no GDB stub) located the entire
text-rendering pipeline within minutes once the trace was driven into
an active typewriter frame.

### Tooling

- `trace_glyph_writes.lua` — drives the 2024 ROM into Oak's intro
  dialog, detects the first frame whose EWRAM glyph cache hash differs
  from the prior frame (= typewriter ticked), then enters single-step
  mode. Each step samples the cache via `emu:readRange`; on any change
  it dumps PC + r0..r12 + cpsr + the byte deltas to JSONL. Captured 374
  events in 5M instruction window.
- `analyze_glyph_trace.py` — clusters events by PC, distributions of LR
  (caller return), cache addresses written, and ROM-pointer-looking
  registers. Shows disasm window around each hot PC.
- `disasm_around.py` — small capstone Thumb disassembler with
  literal-pool resolution (`ldr Rd, [pc, #imm]` → resolved value).
- `extract_jamo_handler_pools.py` — walks each of the 6 jamo handlers
  identified by the dispatcher and extracts every PC-relative LDR's
  resolved value, flagging entries in the patched region.

### What the trace revealed

**370 of 374 events** have `lr = 0x08005c09`, meaning the writes happen
inside a function that is called from `bl #0x8003028` at site
`0x08005c04`. That call site is itself inside a 7-way jump-table
dispatcher whose entry is at **`0x080057a4`** — the rendering function
for one text-window mode (mode byte at `[r6+0x1c]`, with `r6` =
rendering-context struct, observed runtime value `0x02020010`).

**Pipeline:**

```
Text source byte
    ↓ (dispatcher 0x080057a4 chooses jamo handler 0..5 by [r6+0x1c])
Jamo handler @ {0x800645c, 0x8006504, 0x80065cc, 0x8006738, 0x8006800, 0x800696c}
    ↓ (loads font_base + cp*64; calls decoder twice)
Glyph decoder 0x08002fa0 (LUT-driven)
    ↓ (writes 32 bytes per call into IWRAM staging at 0x03003da0)
IWRAM staging 0x03003da0
    ↓ (row blitter 0x08003028 reads, OR-merges 4bpp pixels)
EWRAM glyph cache 0x02007800..0x02009000
    ↓ (later DMA helper at file 0xc79ac..0xc9528)
VRAM tiles 0x06007910...
    ↓
Visible dialog text
```

The two-write-per-cache-byte pattern (`00 → 01 → 21`, `00 → 02 → 22`)
that we predicted theoretically (jamo composition: each pixel byte
holds two layered jamo strokes via 4bpp OR-merge) is now confirmed at
the assembly level — it falls out naturally from the row blitter's
`andimm-orr-strb` sequence at `0x0800342a..0x0800342e`.

### Patched-region literal addresses (the actual font data)

Every jamo handler has a fast path (`r1 == 1`) using a vanilla-region
font (Japanese kana fallback) and a slow/main path using a
patched-region font. Distinct pairs found:

| atlas | font_base | width_table | gap | likely role |
|-------|-----------|-------------|-----|-------------|
| 0     | `0x08edf800` | `0x08f17800` | `0x38000` | hangul, primary |
| 1     | `0x08f18800` | `0x08f50800` | `0x38000` | hangul, secondary |
| 2     | `0x08f51800` | `0x08f89800` | `0x38000` | hangul, tertiary |

Each glyph is 64 bytes in the atlas, only first 32 used. The other 32
may be a different rendering size (small/large) or unused padding.

### Exact encoding (verified by rendering)

After dumping the ROM LUT @ `0x081ea090` (256 bytes) and the IWRAM LUT
@ `0x03000a40` (512 bytes; populated at boot — pulled at frame 700 via
`dump_luts.lua`), the decoder behaviour is fully reduced:

- **Pixel format:** 2 bits per pixel, **MSB-first** within each byte.
  - pixel 0 (leftmost in 4-pixel run) = bits 6-7
  - pixel 1 = bits 4-5
  - pixel 2 = bits 2-3
  - pixel 3 = bits 0-1
- **Byte order per row:** stored as 16-bit big-endian halfwords. The
  decoder loop at `0x08002faa..0x8002fd6` reads `byte[+1]` (high byte
  of the BE halfword) before `byte[+0]`, so for a row of 8 pixels the
  `+1` byte holds the LEFT 4 pixels and the `+0` byte holds the right
  4 pixels.
- **Tile organisation:** **8x8 2bpp tiles**, 16 bytes per tile (8 rows
  × 2 bytes/row).
- **Glyph layout:**
  - Atlas 0 (`0x08edf800`): 2 tiles per glyph laid out side-by-side =
    **16x8** strip — these are *jamo half-cells*. Used by handler 0
    when the engine is composing syllables jamo-by-jamo.
  - Atlas 1 (`0x08f18800`) and Atlas 2 (`0x08f51800`): **4 tiles in
    GBA reading order** (top-left, top-right, bottom-left,
    bottom-right) = **16x16** glyphs. These hold full pre-composed
    hangul syllables plus ASCII (`0-9`, `!?A-Za-z`), accented Latin
    (Ä, Ö, Ü, ñ, é, etc.), arrows, brackets, and Pokémon-specific
    indicators.
- **Color remap** (via the two LUTs — verified empirically by walking
  every input byte through both):
  - raw 2bpp 0 → 4bpp 0 (transparent / paper)
  - raw 2bpp 1 → 4bpp 2 (foreground color A)
  - raw 2bpp 2 → 4bpp 3 (foreground color B — used for the gray
    arrow indicators; almost all hangul uses only color A)
  - raw 2bpp 3 → 4bpp 0 (treated as transparent; unused in real data)
- **Per-glyph width:** `width_table[cp]` gives the advance in pixels
  (typically 5 for narrow ASCII, 6 for hangul/wide-Latin).
- **Atlas slot stride:** 64 bytes per glyph in *every* atlas. Atlas 0
  uses only 32; the other 32 are padding (or a higher-resolution
  variant the renderer doesn't currently sample).

`render_jamo_atlas.py` implements this exactly. Calling it with the
default flags writes 4x-zoomed PNGs of the first 256 entries of each
atlas to `/tmp/poketrek_trace/atlas_render/`. The atlas-1 sheet shows
clean, readable hangul (e.g., 아 르 레 이 니 소 조 사 터 리 보 스 카
치 마 지 나 제 례 케 에 시 개 ...) plus the full ASCII range.

### Implications for codepoint coverage

The dialog corpus's BE codepoints in `0x3700..0x40FF` index into
**atlas 1 or 2** (the dispatcher routes by `[r6+0x1c]` mode byte).
With the renderer above, every codepoint can now be visualised
directly from the ROM, and OCR can resolve the ~460 still-unknown
codepoints against a hangul recognition pipeline. This unblocks the
push from 81% → ~95%+ coverage that was deferred earlier.

### Files added in this update

- `trace_glyph_writes.lua` — runtime single-step tracer with cache
  hash detection and per-step register capture.
- `analyze_glyph_trace.py` — clusters JSONL events by PC, finds caller
  patterns via LR distribution.
- `disasm_around.py` — quick Thumb disassembly with literal pool
  resolution.
- `extract_jamo_handler_pools.py` — extracts patched/vanilla atlas
  pointers from each of the 6 dispatcher handlers.
- `dump_luts.lua` — drives ROM into a known-stable frame and captures
  ROM LUT (`0x081ea090`, 256 B), IWRAM LUT (`0x03000a40`, 512 B), and
  the post-init IWRAM staging buffer.
- `render_jamo_atlas.py` — exact-encoding renderer that decodes any
  glyph slot to a PIL `Image`. Validated against atlas 1 (full hangul
  + ASCII visible).
