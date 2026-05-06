Change of tack: rip the Korean LeafGreen dialog corpus

Context

Phase 2 of moneo is "✅ done" on paper (Moneo-몬어.md:11) but actually has a precise un-bridged gap. The design doc names it bluntly:

▎ CRITICAL: Two separate encodings exist. ROM text uses pages F1–F6 in a custom glyph order. VRAM rendering uses pages F0–F9 in KSX1001 sequential order (validated 8/8 characters). The text engine translates between them at render time. The
▎ translation formula is not yet reverse-engineered.
▎ — Moneo-몬어.md:178

We have:

- All 9,999 dialog records as raw bytes (.moneo-artifacts/rom-text-ko-raw.json, 2,436 distinct codes)
- A 94%-accurate VRAM-side charmap in KSX1001 order (.moneo-artifacts/ksx1001-charmap.json — design doc says VRAM ordering is KSX1001, validated 8/8)
- A working live VRAM fingerprint decoder (KoreanCharmap.kt + VramTextReader.kt) with 46 hand-confirmed entries
- The Thumb text-engine entry point at ROM 0x384800 (handles F1–F6, stores page at 0x03007E3F, then dispatches via a literal pool to a function elsewhere in ROM)
- mGBA 0.10.5 installed with full GDB remote-stub support (-g)

What's been tried and stalled: bespoke Python pipelines that render font glyphs and OCR them with Tesseract (tools/render_dialogue_v6/v7/v8.py, tools/build_charmap.py, tools/build_glyph_table.py). These produce ~85–94% glyph coverage with
systematic OCR errors (50+ glyphs collapsing to "래"). Iterating on this approach is the spinning the user is rightly frustrated by.

The change of tack: stop reverse-engineering the font; use the ROM's own text engine as the oracle, either by disassembling its tiny translation routine or by hooking it live under mGBA's GDB stub. Both are well-trodden community-standard
paths and avoid bespoke OCR.

Recommended approach

Two paths in priority order. Path 1 first because the engine is small (~256 bytes of Thumb at 0x384800) and produces a definitive offline answer; Path 2 as fallback if disassembly hits an indirection wall.

Path 1 — Disassemble the engine, find the in-ROM translation table

The engine at 0x384800 is already partially decoded (page-handling logic is clean Thumb). What's missing is the dispatch target — where the per-page (or per-(page, idx)) translation happens. That target either:

- (a) Indexes a static LUT in ROM → read it directly, done
- (b) Computes the translation procedurally → read the formula off the disassembly, apply it, done
- (c) Uses a multi-level indirection → fall back to Path 2

Steps:

1.  Install Ghidra (brew install --cask ghidra — user pre-approved) and load the Korean ROM as a raw GBA binary (load address 0x08000000, ARM v4T / Thumb). Disassemble starting at 0x08384800.
2.  Resolve the literal-pool loads at 0x38481E and 0x384824. The actual dispatch target is the value at one of these pool slots; the design doc misidentified 0x03007E3F as the page-byte storage but did not chase the dispatch target itself.
3.  Disassemble that target. Find the (page, idx) → glyph_id mapping — either as a tabular blob or as arithmetic.
4.  Read the table (or apply the formula) for all page ∈ {1..6}, idx ∈ {0..251} → produce (page, idx) → ksx1001_position.
5.  Cross with .moneo-artifacts/ksx1001-charmap.json (existing, 94% template-matched, validated as VRAM ordering by design doc) → produce (page, idx) → Hangul.
6.  Decode all 9,999 records in rom-text-ko-raw.json through this map. Handle control bytes per Moneo-몬어.md:163-170 (0xFA/0xFB scroll/clear, 0xFC ext, 0xFD vars, 0xFE LF, 0xFF terminator).
7.  Output app/src/main/assets/moneo/corpus.ko.json.

Deliverables:

- tools/moneo/disasm_engine.md — short writeup of the engine + LUT location
- tools/moneo/build_corpus.py — applies the map to rom-text-ko-raw.json, emits corpus.ko.json
- app/src/main/assets/moneo/corpus.ko.json — full corpus, ~9,999 records

Path 2 — Live trace via mGBA GDB stub (fallback)

If Path 1's dispatch chain is too tangled, switch to live tracing. mGBA Lua does not expose breakpoints (verified — only frame callbacks + memory reads), but the -g flag exposes a full GDB remote stub with hardware breakpoints and watchpoints
(port 2345).

Steps:

1.  Launch headless: mGBA -g 'Pocket Monsters - LeafGreen (Korean).gba'
2.  tools/moneo/dialog_trace.py connects via Python's stdlib socket to localhost:2345 using the GDB remote serial protocol (text-based, ~50 LOC for the subset we need: continue/break/read-memory/read-register/set-hwbreak).
3.  Set hardware execution breakpoint at the engine's per-syllable handler (the dispatch target identified during the static work above, even if Path 1's chain ends in indirection — the first hop after the page-byte load is enough).
4.  Set hardware execution breakpoint at the engine's per-syllable handler (the dispatch target identified during the static work above, even if Path 1's chain ends in indirection — the first hop after the page-byte load is enough).
5.  On each break: read r3 (idx byte), [0x03007E3F] (current page), and queue. After ~16 frames, read VRAM screenblock-31 + charblock-0 and pair the recent (page, idx) sequence with the just-rendered tile groups (existing VramTextReader
    Kotlin logic ports cleanly to Python — same SHA-256 of 128-byte tile-group bytes).
6.  User plays manually with the script attached for 20–30 minutes covering Pallet → Pewter (heavy dialog density), or load any existing save state and hold A through dialogs.
7.  Build (page, idx) → fingerprint table; cross with ksx1001-charmap.json to get → Hangul.
8.  Apply to all 9,999 records as in Path 1.

This is the user's "run the game and read RAM" path, implemented with the standard community tooling (mGBA + GDB).

Out of scope

- More iterations of render_dialogue_v\*.py or new glyph-table-v2.json (this is the spinning).
- New OCR pipelines (Tesseract, Apple Vision, etc.).
- Phase 3 (example sentences) and Phase 4 (Korean ROM hard area gate).
- In-app changes to VramTextReader / KoreanCharmap / MoneoOverlay — they already work; we're producing the corpus they consume.

Deferred follow-on (next session, not this plan)

Wire an in-app auto-bootstrap loop per the design doc's own line 87: VramTextReader already reads VRAM; extend it to also read the dialog buffer (one new calibration: Korean-ROM gStringVar4 address). Each rendered dialog yields (ROM bytes,
VRAM fingerprints) pairs that auto-extend ko_charmap.json and self-correct the offline corpus.

Critical files

Read / disassemble:

- Pocket Monsters - LeafGreen (Korean).gba — engine at 0x384800, dispatch literals at 0x384920 / 0x384924 / 0x384928, font pointer table at 0x38492C, font pages at 0x780000–0x798000
- .moneo-artifacts/ksx1001-charmap.json — VRAM-side ground-truth Hangul mapping (use as-is)
- .moneo-artifacts/rom-text-ko-raw.json — input to build_corpus.py

New:

- tools/moneo/disasm_engine.md
- tools/moneo/build_corpus.py
- tools/moneo/dialog_trace.py (only if Path 2 needed)
- app/src/main/assets/moneo/corpus.ko.json

Reuse (no changes):

- app/src/main/java/com/poketrek/moneo/corpus/KoreanCharmap.kt
- app/src/main/java/com/poketrek/moneo/corpus/VramTextReader.kt
- app/src/main/java/com/poketrek/moneo/data/MoneoRepository.kt (only consumes corpus.ko.json)

Verification

- Spot-check 10 decoded records against existing tools/render_dialogue_v8.py output and known tutorial line "상하좌우로 움직이거나 항목을 선택합니다。" — must match grammatically.
- The 46 entries in app/src/main/assets/moneo/ko_charmap.json (live-VRAM-confirmed) project to specific (page, idx) codes via the new map; those codes' decoded Hangul must match the existing fingerprint→Hangul entries. Any mismatch = the LUT
  or KSX1001 alignment is wrong.
- ./gradlew test green (no Kotlin code changes; this is just an asset file).
- Open the app on emulator, navigate to Moneo, confirm the corpus loads and MoneoRepository.totalDueCount reflects the larger corpus.
- For Path 2 only: tools/moneo/dialog_trace.py --self-test connects to mGBA, sets a no-op breakpoint at 0x384800, reports a hit on the first dialog, exits cleanly.
