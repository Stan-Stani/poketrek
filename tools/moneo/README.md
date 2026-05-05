# Moneo: Korean LeafGreen Text Engine Reverse Engineering

This directory contains tools for capturing, decoding, and translating Korean
text from *Pocket Monsters - LeafGreen (Korean)*. The eventual goal is a
Korean→English glyph map and corpus suitable for in-app translation overlays.

## Status (as of 2026-05-05)

**What works:**

- Native libmgba capture tool (`mgba_capture/`) attaches a Thumb breakpoint at
  the prebyte handler `0x08384818` (after the page-byte store, with `r0` =
  string pointer) and reads `(page, idx)` byte pairs directly via the bus.
  Mailbox cross-check is 100% agreement.
- Periodic framebuffer dumps via `--dump-fb-dir` / `--dump-fb-every` capture
  rendered text screens for ground-truth alignment.
- Token-burst → framebuffer-OCR alignment (`align_union.py`) accumulates votes
  for each `(page, idx)` slot and produces a high-confidence map.
- Blit-table layout was decoded and verified
  (`verify_blit*.py`, `blit_match2.py`): table1 at ROM file offset `0x1CDF1C`
  (256 bytes), table2 at IWRAM offset `0x0A40` (256 halfwords). Layout
  `perm=(TL, TR, BL, BR), hi_first=False` is correct. This gives an offline
  path from `(page, idx)` → expected raw glyph bitmap.

**What was discarded (verified bogus):**

- `ko_charmap.json` (45 entries, prior work): 0/45 fingerprints matched any
  live VRAM tile group across 50 000 captured snapshots.
- Per-glyph Tesseract OCR map (`glyph-map-ocr.json`, 1349 entries): produced
  by an early script that read raw ROM bytes (without blit-table expansion)
  AND used incorrect page strides. Replaced by `path_c_ocr.py`.
- Per-glyph Tesseract OCR map v2 (`path_c_ocr.py`, 1472 entries with verified
  rendering): 0/81 agreement with ground-truth verified entries. Tesseract
  cannot reliably OCR 16x16 Korean glyphs in isolation even when the
  rendered bitmap visually matches the correct character. Path C is
  fundamentally limited by per-glyph OCR accuracy. Sheet
  (`/tmp/sheet_p1.png` style) is useful for HUMAN visual labeling but not
  for automated OCR.

**Current `glyph-map.json`**: 88 entries, all from union-of-captures
ground-truth alignment. This is small but verified — every entry is backed by
≥ 2 alignment votes against on-screen Korean text OCR'd from real game
framebuffers.

**Corpus coverage**: 86 % of bytes decoded (mostly ASCII control codes and the
88 known Korean glyphs). The other ~14 % are real Korean glyphs whose
`(page, idx)` slot has not yet been observed in alignment runs.

## Pipeline

```
ROM + savestate ──► mgba_capture ──► capture-*.json   (token stream)
                                  └► dumps/fb-*.bin   (per-frame screenshots)

  capture-*.json ┐
  fb-*.bin       ├─► align_union.py ──► glyph-map-union.json
                                          (verified votes, ≥ 2 OCR matches)
                                          │
                                          └─► tools/moneo/glyph-map.json
                                                 │
                                                 └─► build_corpus.py
                                                       │
                                                       └─► app/src/main/assets/
                                                            moneo/corpus.ko.json
```

## How to extend coverage

The bottleneck is **getting more variety of in-game text**. Captures so far
either hit the title screen or get stuck in the bedroom intro tutorial,
yielding only ~115 unique `(page, idx)` slots. To grow the map:

1. **Better press scripts**. Each press list entry holds for 30 frames then
   releases for 10 (one cycle = 40 frames). Walking a single tile takes ~16
   pressed frames, so a single DOWN entry is barely one tile. Use long runs of
   directional entries plus periodic A to actually progress past the bedroom
   into NPC dialogue.
2. **Pre-progressed save**. The `.sav` next to the ROM is loaded
   automatically. Manually playing further into the game and saving will
   expose new dialogue under the same script.
3. **Multiple captures, union**. `align_union.py` already merges results
   across `capture-{fb,walk,fresh,long-aligned}.json`. Add new captures to its
   `CAPTURES` list.
4. **Path B, fully exploited**. The blit-table verification gives an offline
   `(page, idx) → raw glyph bitmap` function (`blit_match2.py`,
   `path_b_label.py`). However, **live VRAM tiles do not match blit output
   byte-for-byte** — the engine OR-composites the glyph mask with shadow
   color `0x44` (palette index 4) before writing to VRAM. So
   `live_vram_tile == blit_output | shadow_fill_pattern`. To use blit fps for
   live group matching, the matcher must apply the same compositing or strip
   shadow pixels from live data first. Not yet implemented; Path A
   (alignment) currently outperforms because OCR'd ground truth from FB
   matches what's actually on screen regardless of compositing.

## Files

- `mgba_capture/capture.c` — native libmgba capture, single-source build via
  `cmake --build build/`. Flags: `--rom`, `--out`, `--frames`, `--press`,
  `--dump-iwram`, `--dump-vram`, `--dump-fb`, `--dump-fb-dir`,
  `--dump-fb-every`.
- `align_union.py` — primary alignment pipeline. **Use this.**
- `align_tokens.py`, `align_tokens2.py`, `align_tokens3.py` — earlier
  iterations; kept for reference.
- `ocr_all_glyphs.py` — per-glyph Tesseract OCR (verified unreliable; output
  in `glyph-map-ocr.json` for comparison only).
- `path_c_ocr.py` — render every (page, idx) glyph from blit-table-expanded
  pixel data and OCR with Tesseract. Result: 1472 entries, 0/81 agree with
  verified — **do not use as data source**, but the rendering function
  (`render_glyph(p, i)`) is correct and useful for visual review or future
  manual labeling. Output: `.moneo-artifacts/glyph-map-pathC2.json`.
- `build_corpus.py` — turns `glyph-map.json` + ROM-extracted records into
  `corpus.ko.json`.
- `verify_blit*.py`, `blit_fp*.py`, `inspect_*.py`, `disasm_blit.py` —
  blit-table decoding and verification harness.
- `glyph-map.json` — **canonical**, 88 entries, ground-truth verified.
- `glyph-map-old.json` — previous bogus per-glyph-OCR map (kept for diff).

## Verified facts about the engine

- Page-byte mailbox at IWRAM `0x03007E3F`.
- Prebyte handler at `0x08384800` (Thumb), main render at `0x080062B4`.
- Font pointer table at `0x0838492C`, 7 entries:
  - `[0]` = `0x081DEEE8` — non-Korean base font (numerals/ASCII/symbols).
  - `[1..6]` = Korean pages F1..F6 at `0x08780000`, `0x08784000`,
    `0x08788000`, `0x0878C000`, `0x08790000`, `0x08794000`. Stride
    `0x4000` = 16 KB per page = 256 glyphs.
- **Page byte (`0xF1..0xF6`) `p` selects font pointer index `p`** in the
  table, i.e. token `0xF1, idx` resolves to font pointer `[1]` = page F1
  base `0x08780000`.
- Glyph layout per page: 8 glyphs per horizontal stripe of 512 ROM bytes.
  TL/TR sub-tiles in the first 256 bytes (8×32), BL/BR in the next 256.
  For glyph index `i`: stripe `= i // 8`, col `= i % 8`,
  base `= page_base + stripe*512 + col*32`,
  TL=`base+0`, TR=`base+16`, BL=`base+256`, BR=`base+272`.
  Each ROM sub-tile is 16 bytes 2bpp; runtime expands via blit tables to
  32 bytes 4bpp.
- **Blit tables**: `table1` at ROM `0x081CDF1C` (256 bytes, ROM byte →
  pattern_idx 0..80). `table2` at IWRAM `0x03000A40` (256 halfwords,
  pattern_idx → packed 16-bit 4bpp pixels). Pixel value `1` is the
  runtime background, `2` is glyph dark, `3` is glyph mid; value `0` is
  rare/unused.
- Text strings live at `0x081A....` (compressed ROM blocks) and
  `0x083D....` (game text bank).
- Each text byte 0xF1..0xF6 = page select; following byte = glyph index 0..255.
- Other reserved bytes: `0xFF` end, `0xFC/FD/F7/F8/F9` two-byte var/format
  escapes. ASCII `0x20..0x7E` range encodes ASCII + control codes.
