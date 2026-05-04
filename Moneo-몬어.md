# Moneo / 몬어 — Korean Language Learning Mode

A new in-app mode layered on top of the existing emulator. Separate from and decoupled from the step-counting feature — the goal is that it can eventually be forked into its own module or app. MVP ships with **manually-seeded** Korean vocab and a soft on-screen study gate. Harder gating, a ROM-extracted corpus, and example sentences are later phases.

## Status (May 2026)

| Phase | Title                                      | Status                            |
| ----- | ------------------------------------------ | --------------------------------- |
| 0     | Skeleton & toggle                          | ✅ done                           |
| 1     | SRS core + soft gate                       | ✅ done                           |
| 2     | Corpus extraction / live VRAM decoder      | ✅ pivoted to VRAM, charmap done  |
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

### Korean ROM is encrypted (`YJencrypted`)

The shipped Korean ROM (`Pocket Monsters - LeafGreen (Korean).gba`) is a self-decrypting "YJ" group dump:

- GBA header title field (offset `0xA0`) reads the literal ASCII string `YJencrypted` instead of `POKEMON LEAF`.
- File is 16 MB + 0x14DC bytes — shifting by 0x14DC does **not** yield plaintext.
- Nintendo logo at `0x04–0xA0` is intact and the branch at `0x00` is a real ARM `B` into the encrypted body — an in-ROM boot stub decrypts at runtime.
- Searched for `POKEMON`/`LEAFGREEN`/`포켓몬` under: Gen3 charmap, UTF-16LE, EUC-KR, CP949 → **zero hits** in the entire file.
- US vs Korean byte similarity at the same offset is ~22 % (random noise would be ~0.4 %, same-build dumps would be ~99 %) — confirms selective scramble, not garbage.
- mGBA has no awareness of the `YJencrypted` scheme and does not descramble. The ROM's own stub runs, decrypts into EWRAM/IWRAM, then jumps to the real entry point.

**Static rip is infeasible** without reverse-engineering the in-ROM decryptor (estimated multi-day work; no public tooling found).

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

The charmap is bootstrapped but small:

- **Coverage.** ~34 syllables — enough to validate the pipeline, far from full Korean text. The next dialogs encountered in-game will surface unknown fingerprints (logged as `?` by the decoder); each one needs ~30 s of screenshot + manual labelling.
- **Ambiguity.** `때` and `니` collide on fingerprint `6847b2f87293526b` in one capture; the conflicting entry was dropped pending re-capture from a context where each is unambiguous.
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
