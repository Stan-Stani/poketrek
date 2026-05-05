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
- Blit-table layout was decoded and verified in live VRAM
  (`verify_blit*.py`): table1 at ROM file offset `0x1CDF1C` (256 bytes), table2
  at IWRAM offset `0x0A40` (256 halfwords). Layout B confirmed on 5 raw bytes.
  This gives an offline path from `(page, idx)` → expected VRAM bitmap.

**What was discarded (verified bogus):**

- `ko_charmap.json` (45 entries, prior work): 0/45 fingerprints matched any
  live VRAM tile group across 50 000 captured snapshots.
- Per-glyph Tesseract OCR map (`glyph-map-ocr.json`, 1349 entries): disagreed
  with aligned ground truth on 35/35 first samples. Tesseract cannot reliably
  read 8 × 8 GBA font glyphs in isolation.

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
   `(page, idx) → VRAM bitmap` function. Matching that bitmap against live
   tile groups captured in the same run would let us label tokens without
   needing the FB to render the same string the token came from. This is not
   yet wired up end-to-end (PMI alignment failed at the snapshot-every=30
   timing resolution).

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
- `build_corpus.py` — turns `glyph-map.json` + ROM-extracted records into
  `corpus.ko.json`.
- `verify_blit*.py`, `blit_fp*.py`, `inspect_*.py`, `disasm_blit.py` —
  blit-table decoding and verification harness.
- `glyph-map.json` — **canonical**, 88 entries, ground-truth verified.
- `glyph-map-old.json` — previous bogus per-glyph-OCR map (kept for diff).
- `glyph-map-ocr.json` — raw per-glyph OCR output (do not use).

## Verified facts about the engine

- Page-byte mailbox at IWRAM `0x03007E3F`.
- Prebyte handler at `0x08384800` (Thumb), main render at `0x080062B4`.
- Font pointer literals at `0x0838492C`: F1=`0x08780000` … F6=`0x08794000`.
- Text strings live at `0x081A....` (compressed ROM blocks) and
  `0x083D....` (game text bank).
- Each text byte 0xF1..0xF6 = page select; following byte = glyph index 0..255.
- Other reserved bytes: `0xFF` end, `0xFC/FD/F7/F8/F9` two-byte var/format
  escapes. ASCII `0x20..0x7E` range encodes ASCII + control codes.
