# Moneo / 몬어 — Korean Language Learning Mode

A new in-app mode layered on top of the existing emulator. Separate from and decoupled from the step-counting feature — the goal is that it can eventually be forked into its own module or app. MVP ships with **manually-seeded** Korean vocab and a soft on-screen study gate. Harder gating, a ROM-extracted corpus, and example sentences are later phases.

## Status (May 2026)

| Phase | Title                                      | Status                            |
| ----- | ------------------------------------------ | --------------------------------- |
| 0     | Skeleton & toggle                          | ✅ done                           |
| 1     | SRS core + soft gate                       | ✅ done                           |
| 2     | Corpus extraction / live VRAM decoder      | ✅ ROM rip done; VRAM decoder live |
| 3     | Bundled example sentences                  | not started                       |
| 4     | Hard area gate (Korean ROM calibration)    | not started                       |

Phases 0–2 are committed and the build is green.

---

## Phase 0 — Skeleton & Toggle ✅

Settings sheet section with "Korean learning mode" toggle + "Open Moneo" button. Full-screen `MoneoOverlay` Composable. `MoneoPrefs` (DataStore, separate file from `movement_budget`). `MoneoModule` singleton wired in `EmulatorActivity`.

---

## Phase 1 — SRS Core ✅

- **SM-2 scheduler** (`moneo/srs/Sm2.kt`) — pure Kotlin, JVM unit-tested (9 tests). Learning steps `[1 min, 10 min]`, ease floor 1.3, graduating interval 1 d / easy interval 4 d.
- **Data layer** — `VocabEntry`, `CardRecord`, `AreaProgress` in `moneo/data/`. JSON-on-disk persistence via `MoneoCardStore` (atomic tmp-rename writes); chose this over Room to avoid adding KSP. `MoneoRepository` exposes `dueCards`, `totalDueCount`, `dueCountForArea` as StateFlows.
- **Seed corpus** — `app/src/main/assets/moneo/seed-vocab-ko.json` (~45 hand-curated entries with RR romanization). `app/src/main/assets/moneo/areas.json` — 6 areas: Pallet Town → Pewter City.
- **Review UI** — `MoneoOverlay` (area picker grid) → `ReviewScreen` (front / reveal / 4-button grading). Romanization toggle.
- **Soft gate HUD** — `MoneoHud` renders "복습 N" badge when there are due cards. Tap opens overlay. Does **not** mask emulator input.
- **Fork hygiene** — `com.poketrek.moneo.*` has zero imports from `com.poketrek.step.*`. Only `EmulatorActivity` and `EmulatorScreen` cross the boundary.

---

## Phase 2 — Corpus Extraction ✅

### Static ROM rip ✅ — text IS plaintext (the `YJencrypted` label is misleading)

Earlier conclusion that the ROM was XOR-scrambled was **wrong**. The header title field at `0xA0` literally reads `YJencrypted` because the YJ patcher tags every dump it touches, but the rest of the file is plaintext byte-for-byte. The reason the previous searches for known charsets (Gen3, EUC-KR, CP949) failed was that the Korean fan translation uses its own custom 2-byte encoding, not any standard Korean charset.

**Encoding scheme** (saved in `assets/moneo/ko-encoding-schema.json`):

- Korean syllables are encoded as 2-byte pairs `(HI, LO)` where `HI ∈ 0xF0..0xFC` selects a "page" and `LO ∈ 0x00..0xFF` indexes into that page.
- `0x00..0x0F` = single-byte formatting / NULL / line feed.
- `0xAB`, `0xAD` = end-of-phrase (wait-for-A-button).
- `0xFD XX` = 2-byte expansion command (e.g. swap text colour, insert player/trainer name).
- `0xFE` = sub-record separator (line break inside a multi-line dialog).
- `0xFF` = record terminator.

**Rip stats** (saved in `assets/moneo/ko-syllable-codes.json`):

- 9,999 dialog records across 107 text regions (mainly `0x3DF800-0x4D5000`, `0x35D800-0x36BFFF`, scattered `0x47x000-0x4Cx000`).
- 50,200 total Korean syllables.
- 2,436 distinct syllable codes (matches the expected ~2-3K syllable count for a Pokémon-sized vocab).
- Per-page distribution: F0 = 7,992 (~71% of which is `F001` = the SPACE pair); F1 = 14,112 (the densest Hangul page, ~250 distinct lo-bytes); F2-FC tail off in frequency.
- Raw byte dump retained at `.moneo-artifacts/rom-text-ko-raw.json` (15.7 MB, gitignored — too big for the APK).

**What the ROM rip does NOT yet give us**: the `(page, lo) → Hangul Unicode` mapping. The ROM stores text with its own custom code-table; the Korean glyphs themselves live in a font block we have not yet located in the ROM (likely behind a non-standard transform — neither raw nor BIOS LZ77; see `/tmp/moneo-rip/font_found.json` for what was tried). The runtime VRAM-fingerprint decoder (next section) is currently the only way we have to assign codes to characters.

### Pivot — live runtime EWRAM capture

Because mGBA runs the ROM's decryptor faithfully, EWRAM is plaintext once the game is running. The Phase 5 "live RAM capture" concept was promoted to fill Phase 2.

Implemented: `com.poketrek.moneo.corpus.RamCapture`

- Own coroutine + `SupervisorJob` scope; polls 256 KB EWRAM (`0x02000000`) every 500 ms.
- Diffs against prior snapshot; emits contiguous changed runs ≥ 12 bytes (terminator-trimmed, CRC-deduped via ring buffer).
- Appends records to `filesDir/moneo/capture.bin` in a simple framed format: `KCAP` magic header + per-record `[u32 ts, u32 addr, u32 len, u32 crc32, u8[len] bytes]`.
- `CaptureReader.kt` is a pure-JVM decoder usable as a host-side dev tool after `adb pull /data/data/com.poketrek/files/moneo/capture.bin`.
- Dev panel row in Moneo settings section: capture toggle + run counter + reset.
- `RamCaptureTest` verifies a synthetic 30-byte EWRAM diff produces at least one record.

### Pivot — pixel-fingerprint VRAM decoding

ROM byte encoding turned out to be **the wrong primitive**. EWRAM/IWRAM scans for ROM text pointers found audio and sprite-animation tables but no Korean text strings — tutorial pages appear to be pre-rendered Hangul tile graphics rather than dynamically encoded text. Rather than chase a hypothetical Gen3-KO charmap, we extract glyphs directly from VRAM:

- **Tile structure.** Korean LeafGreen renders dialog text on a BG layer with `screenbase = 31` (tile-index map at `0x0600F800`) and `charbase = 0` (glyph pixel data at `0x06000000`). Each Hangul character is a 2×2 tile block (16×16 px, 4 bpp = 128 bytes total).
- **Fingerprinting.** SHA-256[:16] over the concatenated 128 bytes of a 4-tile group uniquely identifies a rendered glyph. Pixel data is identical across re-renders of the same character (same glyph, same palette index pattern).
- **Charmap derivation.** Two VRAM dumps were captured during the in-game tutorial pages, then cross-referenced with the known on-screen text (`상하좌우로 움직이거나` / `항목을 선택합니다。` / etc.) to build `assets/moneo/ko_charmap.json` — 45 fingerprint→char entries covering 34 Hangul syllables + the ideographic full stop. 19/19 chars from the shared tutorial line decoded identically across both dumps, confirming fingerprint stability.
- **Runtime decoder.** `KoreanCharmap.kt` loads the asset, `VramTextReader.readLines(reader, charmap)` does a single 64 KB bus read and decodes up to 7 text row-pairs in one shot. The HUD's debug panel exposes a **"Decode KO"** button that prints the current screen's text to logcat — used to expand the charmap incrementally as new dialogs are encountered.

### What's still missing for Phase 2

We now have BOTH halves: the encoded text bytes from the ROM (2,436 distinct codes) AND a fingerprint-based VRAM decoder. The remaining work is to **bridge** them so codes can be auto-mapped to Hangul:

- **Auto-map (page, lo) → Hangul.** Walk the dialog records in `.moneo-artifacts/rom-text-ko-raw.json`; for each record that the engine has just rendered (live RAM matches the ROM bytes), use the existing `VramTextReader` to read the displayed glyphs, then assign each `(page, lo)` code in the record to its visible Hangul. Once a few dozen dialogs have been seen this way, the entire 2,436-code table will be filled.
- **Pixel-fingerprint coverage.** Currently ~34 syllables in `ko_charmap.json`. With the auto-map loop above, every distinct on-screen syllable adds to the fingerprint table.
- **Ambiguity.** `때` and `니` collided on fingerprint `6847b2f87293526b` in one capture; the conflicting entry was dropped pending re-capture from a context where each is unambiguous.
- **Vocab discovery loop.** The decoder logs lines but does not yet feed `MoneoRepository`. A simple "unseen-line accumulator" would write decoded strings to `filesDir/moneo/discovered.json` for offline review; that wiring is deferred until coverage warrants it.

---

## Phase 3 — Bundled Example Sentences

Dev-time pipeline: reads vocab JSON, generates TOPIK 1–2 level sentences via LLM (no runtime dep), enforces non-spoiling constraint, outputs `assets/moneo/sentences-ko.json`. Validator Gradle task checks allowed-words constraint at build time. `ReviewScreen` shows one random sentence after reveal.

---

## Text & Font Encoding — Complete Technical Analysis

### How Gen 3 (US/JP) encodes text (baseline)

Sources: [Bulbapedia Character_encoding_(Generation_III)](https://bulbapedia.bulbagarden.net/wiki/Character_encoding_(Generation_III)), [pret/pokefirered](https://github.com/pret/pokefirered) decompilation (`src/text.c`, `charmap.txt`).

**Single-byte encoding (0x00–0xFF):**

| Range       | Content                                                  |
|-------------|----------------------------------------------------------|
| `0x00`      | Space (JP) / null-ish                                    |
| `0x01–0xA0` | Kana (JP) or accented Latin chars (Western)              |
| `0xA1–0xAA` | Digits 0–9                                               |
| `0xAB–0xBA` | Punctuation (`!`, `?`, `.`, `-`, `·`, `…`, `"`, `'`, `♂`, `♀`, `$`, `,`, `×`, `/`) |
| `0xBB–0xD4` | Uppercase A–Z                                            |
| `0xD5–0xEE` | Lowercase a–z                                            |
| `0xEF`      | `►` scroll arrow                                         |
| `0xF0`      | `:` (colon)                                              |
| `0xF1–0xF6` | `Ä Ö Ü ä ö ü` (German accented chars)                   |
| `0xF7`      | Dynamic data escape (FRLG/E only)                        |
| `0xF8`      | Keypad icon escape (FRLG/E only)                         |
| `0xF9`      | Extra symbol escape (FRLG/E only)                        |
| `0xFA`      | Scroll prompt (scroll up, continue)                      |
| `0xFB`      | Clear prompt (clear dialog box, continue)                |
| `0xFC`      | Extended control code (function index + params follow)   |
| `0xFD`      | Variable substitution (player name, buffers, etc.)       |
| `0xFE`      | Line break                                               |
| `0xFF`      | String terminator                                        |

**FC extended functions (key ones):**
- `FC 01 XX` — change text color
- `FC 04 XX XX XX` — set text / highlight / shadow colors
- `FC 06 XX` — change font (`00`=Small, `01`=NormalCopy1, `02`=Normal, `03`=NormalCopy2, `04`=Male, `05`=Female)
- `FC 0C XX` — print extra symbol (glyph from the 0x100+ extended set)
- `FC 15` — switch to Japanese font; `FC 16` — switch to international font

**FD variables:**
- `FD 01` = player name, `FD 02–04` = script buffers, `FD 06` = rival name

**Fonts in the official ROM (from pokefirered `text.c`):**

| Font ID | Name           | Use case                    | Glyph size      |
|---------|----------------|-----------------------------|-----------------|
| 0       | `FONT_SMALL`   | Party screen, Pokédex       | 8×12 (JP) / var×13 (Latin) |
| 1       | `FONT_NORMAL_COPY_1` | General text          | 10×12 (JP) / var×16 (Latin) |
| 2       | `FONT_NORMAL`  | General text                | same as above   |
| 3       | `FONT_NORMAL_COPY_2` | General text          | same as above   |
| 4       | `FONT_MALE`    | Male NPC dialog (sans-serif)| same as above   |
| 5       | `FONT_FEMALE`  | Female NPC dialog (serif)   | same as above   |
| 6       | `FONT_BRAILLE` | Braille puzzles             | 8×16            |
| 7       | `FONT_BOLD`    | Bold (JP only)              | 8×12            |

Font glyph data is stored as binary blobs (`INCBIN`) in the ROM. Japanese/Korean glyphs use 2×2 tile layout (16×16 px) in a **grid format**: glyph offset = `0x200 * (id / 16) + 0x20 * (id % 16)` bytes, with sub-tiles at TL(+0), TR(+16), BL(+256), BR(+272), each 16 bytes of GBA-native packed 2bpp data (4 pixels per byte, low 2 bits = leftmost). Latin glyphs use linear indexing (`0x20 * glyphId`). The `DecompressGlyphTile()` function copies 2bpp tile data and converts to 4bpp for VRAM rendering.

The namu.wiki article confirms: male NPCs use sans-serif font (`FONT_MALE`), female NPCs use serif font (`FONT_FEMALE`). In the US version this is color-differentiated (blue vs pink) rather than font-differentiated.

### How the Korean fan translation re-encodes text

The Korean ROM (YJ-patched) **completely replaces** the text engine with custom Thumb code at ROM 0x384800:

1. **Bytes `0xF1–0xF6` are 2-byte Korean syllable page selectors.** In the official encoding 0xF1–0xF6 were single printable characters (`Ä Ö Ü ä ö ü`). The Korean translation repurposes them as the first byte of a 2-byte Korean syllable code: `(page, index)` where `page ∈ 0xF1..0xF6` (6 pages) and `index ∈ 0x00..0xFB` (252 usable codes per page). The text engine parses: `page_number = byte - 0xF0`, stores it at RAM 0x03007E3F, reads the next byte as the glyph index.

2. **Control characters preserved:**
   - `0x00–0xF0` — single-byte characters (ASCII-like, game-specific char table; ≤0xF0 threshold)
   - `0xFA` — scroll prompt (scroll up, continue)
   - `0xFB` — clear prompt (clear dialog box, continue)
   - `0xFC XX [params]` — extended format (FC 01 XX = color change, etc.)
   - `0xFD XX` — variable substitution (player name, buffers, etc.)
   - `0xFE` — line break
   - `0xFF` — string terminator
   - Bytes `0xF7–0xF9` — also treated as control/single-byte (≥0xF7 threshold)

3. **Actual capacity:** 6 pages × 512 glyph slots = 3,072 possible syllable codes (3,010 non-blank glyphs confirmed). In practice, 1,319 distinct codes are observed across ~41,000 Korean character instances in the text data region. The text engine addresses glyphs using the page's grid layout.

4. **Font data at known ROM location.** 6 font pages at ROM 0x780000–0x798000, each 0x4000 (16KB) = 512 glyphs of 16×16 px in **GBA-native packed 2bpp format** with pokefirered grid layout (glyph offset = `0x200 * (id/16) + 0x20 * (id%16)`, sub-tiles at +0, +16, +256, +272, 16 bytes each = 64 bytes/glyph; each byte = 4 packed pixels, low bits = leftmost). Total: **3,072 glyph slots, 3,010 non-blank, in 96KB**. Font pointer table at ROM 0x38492C.

5. **Per-page distribution:** F1 is the densest page (~22,812 occurrences, 246 unique indices), then F2 (~9,823), F3 (~4,238), F4 (~2,393), F6 (~1,119), F5 (~718).

6. **CRITICAL: Two separate encodings exist.** ROM text uses pages F1–F6 in a custom glyph order. VRAM rendering uses pages F0–F9 in KSX1001 sequential order (validated 8/8 characters). The text engine translates between them at render time. The translation formula is not yet reverse-engineered.

### Why this matters: bridging the encoding gap

We have **two halves** of the puzzle:

| What we have | Source | Count |
|---|---|---|
| All ROM text byte sequences | Script pointer analysis (0x160000–0x1A0000) | 1,319 distinct (F1–F6, index) codes, ~41,000 occurrences |
| Font glyph bitmaps | ROM 0x780000–0x798000 | 3,010 non-blank glyphs (packed 2bpp grid, 512/page × 6 pages), visually confirmed as Korean |
| Pixel → Unicode mapping | VRAM fingerprint decoder (`ko_charmap.json`) | 46 entries (34 unique Hangul + `。`) |
| VRAM encoding formula | Validated from 8 captures | `adj = ksx_pos + 1; page = F0 + adj//252; idx = adj%252` |

The **missing bridge**: `(page, index) → Unicode Hangul` for all 1,319 ROM text codes.

### Strategy to complete the charmap

**Approach 1 — Font glyph rendering + OCR/fingerprint matching (recommended)**

Font data location is now KNOWN: ROM 0x780000–0x798000, 3,010 non-blank glyphs in GBA-native packed 2bpp format.

1. **Font data already located.** 6 pages × 512 glyphs at 0x780000, 0x784000, ..., 0x794000. Format: packed 2bpp with pokefirered grid layout (offset = `0x200*(id/16) + 0x20*(id%16)`, sub-tiles at +0, +16, +256, +272, 16 bytes each = 64 bytes/glyph). Rendering code verified — produces readable Korean syllables.
2. **Extract all 3,010 glyph tiles as 16×16 images.** Rendering code:
   ```python
   # Grid layout: sub-tiles TL(+0), TR(+16), BL(+256), BR(+272)
   # Each sub-tile: packed 2bpp, 16 bytes (8 rows × 2 bytes × 4 px/byte)
   for dx, dy, tile_off in [(0,0,0), (8,0,16), (0,8,256), (8,8,272)]:
       for row in range(8):
           for bidx in range(2):  # 2 bytes per row
               b = rom[off + tile_off + row*2 + bidx]
               for px in range(4):
                   v = (b >> (px*2)) & 0x3  # low bits = leftmost
   ```
3. **SHA-256 fingerprint each glyph.** Match against existing `ko_charmap.json` entries.
4. **For unmatched glyphs:** OCR with Korean model or manual labeling.
5. **Key complication:** Text codes (F1, idx) address glyphs via the grid layout formula within each page. The character ordering is CUSTOM (not KSX1001, not Unicode order). The text engine at 0x384800 translates ROM codes to VRAM codes at render time.

**Approach 2 — Runtime correlation (slower but reliable)**

Play through dialogs. For each:
1. Intercept the ROM text pointer being fed to the text engine (the `(page, lo)` sequence)
2. Simultaneously read VRAM pixels via `VramTextReader`
3. Align byte positions with rendered character positions to assign codes to characters
4. Each new dialog seen adds entries; ~50–100 distinct dialogs would cover most codes

**Approach 3 — Charblock dump at runtime (hybrid)**

Already partially implemented in `RamCapture.snapshotCharblockIfChanged()`:
1. When the game loads a font, the complete glyph data is in VRAM charblock 0 (0x06000000, 16 KB per charblock)
2. Dump all 4 charblocks (64 KB) → extract all loaded glyph tiles
3. Fingerprint each tile group and cross-reference with `ko_charmap.json` known entries
4. The 16 KB charblock holds ~128 glyphs at a time (16384 ÷ 128 = 128 at 4bpp VRAM format — note: ROM stores 2bpp, game converts to 4bpp for VRAM). Multiple captures across different game states would eventually cover all glyphs.

### Implementation plan

The recommended path is **Approach 1** (font tile extraction):

1. Write a JVM tool (`CharmapTool.kt`) that:
   - Scans the Korean ROM binary for the font data area
   - Extracts all glyph tiles, renders them as PNG images
   - SHA-256 fingerprints each and cross-references with existing `ko_charmap.json`
   - Outputs the complete `ko-syllable-codes.json` with `hangul` fields filled

2. For OCR of unknown glyphs, use Tesseract with Korean language model, or render to a contact sheet for manual labeling.

3. Once the complete `(page, lo) → Unicode` mapping exists, a simple decoder can convert the entire ROM text dump into readable Korean — completing the dialog rip for Moneo.

---

## Phase 4 — Hard Area Gate

Depends on Korean ROM map-ID calibration. Identify the Korean ROM equivalent of `SaveBlock1` pointer (`0x03005008` in US Rev1) and `mapBank`/`mapId` offsets. Extend `LeafGreenRam` / add `LeafGreenRamKr`. When Moneo enabled and the current map corresponds to an area with due prereq cards, mask D-pad and surface a "Review required" modal.

---

## Architecture notes

```
EmulatorActivity
  └─ MoneoModule.get(context)      ← singleton, mirrors MovementBudget pattern
       ├─ MoneoPrefs                (DataStore)
       ├─ MoneoRepository           (StateFlow-backed, JSON persistence)
       │    ├─ MoneoCardStore       (filesDir/moneo/cards.json, atomic writes)
       │    └─ SeedLoader           (assets/moneo/seed-vocab-ko.json)
       ├─ MoneoSoftGate             (observe-only, emits Badge for HUD)
       └─ RamCapture (lazy)         (wired via bindCapture { addr, len → busReadBytes })

EmulatorScreen
  ├─ MoneoHud                       (badge overlay, tap to open)
  └─ MoneoOverlay (full-screen)
       ├─ AreaPicker (LazyVerticalGrid)
       └─ ReviewScreen (front → reveal → 4-button grade)
```

**Stable card IDs**: `"<sourceTag>:<korean>"` — survives JSON round-trip and seed-list expansion without breaking SM-2 state.

**Forkability invariant**: `grep -r 'com.poketrek.step' app/src/main/java/com/poketrek/moneo` must return nothing.
