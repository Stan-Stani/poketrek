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
