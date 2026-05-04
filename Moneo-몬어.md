# Moneo / 몬어 — Korean Language Learning Mode

A new in-app mode layered on top of the existing emulator. Separate from and decoupled from the step-counting feature — the goal is that it can eventually be forked into its own module or app. MVP ships with **manually-seeded** Korean vocab and a soft on-screen study gate. Harder gating, a ROM-extracted corpus, and example sentences are later phases.

## Status (May 2026)

| Phase | Title                                      | Status                            |
| ----- | ------------------------------------------ | --------------------------------- |
| 0     | Skeleton & toggle                          | ✅ done                           |
| 1     | SRS core + soft gate                       | ✅ done                           |
| 2     | Corpus extraction spike / live RAM capture | ✅ scaffolded (see blocker below) |
| 3     | Bundled example sentences                  | not started                       |
| 4     | Hard area gate (Korean ROM calibration)    | not started                       |

Phases 0–1 are committed and the build is green. Phase 2 infra is committed.

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

## Phase 2 — Corpus Extraction ⚠️ BLOCKER

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

### What's still missing for Phase 2

The capture infra exists but the **charmap** (byte index → Hangul syllable) has not been derived yet. Two options:

1. **Tile inspector overlay** — show the framebuffer's font tilemap with byte indices overlaid; developer labels characters by visual inspection.
2. **Manual annotation** — pull `capture.bin`, display runs as hex in a dev tool, label against in-game screenshots by hand.

Once ~20–30 characters are mapped, a partial decoder can bootstrap extraction of more text. This is the next concrete action for Phase 2.

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
