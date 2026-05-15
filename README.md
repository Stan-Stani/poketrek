# Moneo · 몬어

An Android app for learning Korean by reading the 2024 fan-translation of Pokémon LeafGreen. Vocabulary and example sentences are mined from the ROM itself, attributed to the in-game area where they surface, and surfaced as a spaced-repetition deck while you play.

The twist: the emulator is **step-gated**. The phone's hardware step counter feeds a movement budget; every overworld tile you move (via the D-pad, as normal) costs one tile from that budget, and when the budget hits zero the direction-pad is masked until you walk in the real world again. You still play the game — you just can't out-walk yourself. The Korean words you'd be encountering at that point in the story queue up for review. The step-gating layer is called **PokéTrek**; Moneo is the Korean-learning experience that runs on top of it.

## Get the app (for players)

> ⚠️ **Pre-release.** Moneo is at **Phase 0** — the emulator embed is scaffolded but not yet validated on real devices. Expect rough edges. There may be no published build yet; check the Releases page below.

You don't need to build anything or know how to code to play.

**What you need:**

- An **Android 8.0+ phone with a hardware step counter** (most phones since ~2016 have one). The step-gating feature only works on a real device — emulators don't report steps.
- Your own **legally-obtained Pokémon LeafGreen ROM**. Moneo never ships a ROM. The Korean learning experience targets the 2024 Korean fan-translation; the English US Rev 1 ROM also runs (but the Korean flashcards stay dormant on it). See [Korean ROM (2024 fan-translation)](#korean-rom-2024-fan-translation) for how to get the Korean ROM.

**Install:**

1. Download the latest APK from the [**Releases page**](https://github.com/Stan-Stani/moneo/releases).
2. On your phone, allow installing from your browser/files app when prompted (Settings → *Install unknown apps*).
3. Open the APK to install, then launch **Moneo**.

**Play:**

1. In the app, go to **Settings → Add ROM** and pick your `.gba` file. Moneo identifies the ROM and turns on the matching features.
2. Play LeafGreen normally with the on-screen D-pad.
3. Every tile you walk in the overworld spends from a **movement budget**. When it runs out, the D-pad locks until you **walk in the real world** — your phone's step counter refills the budget.
4. The Korean words you'd be meeting at that point in the story queue up as a spaced-repetition deck. Review them, then keep playing.

Found a wrong or awkward Korean flashcard? Hit the **✎ Report** button on the review screen — it opens a pre-filled GitHub issue.

---

## Building from source (for contributors)

The rest of this README is for people who want to build, modify, or contribute to Moneo. The full design lives at `~/.claude/plans/i-would-like-to-inherited-papert.md`.

### Status

**Phase 0** — emulator embed scaffolded; not yet validated on-device.

### Prerequisites

- macOS / Linux
- [Android Studio](https://developer.android.com/studio) (Ladybug 2024.2.1 or newer recommended)
- Android NDK `27.2.12479018` (install via Android Studio → SDK Manager → SDK Tools)
- CMake `3.22.1+` (also via SDK Manager)
- A device or emulator running Android 8.0+ (API 26). For step-counter testing, a physical device with a hardware pedometer is required — the Android Emulator does not expose `TYPE_STEP_COUNTER`.

### First-time setup

```bash
# Clone with submodules (mGBA lives under third_party/mgba)
git submodule update --init --recursive

# Drop your legally-obtained LeafGreen ROM here for the Phase 0 test.
# This path is gitignored. The runtime will use a Storage Access Framework picker;
# the test asset is only for `connectedAndroidTest`.
mkdir -p app/src/androidTest/assets
cp /path/to/leafgreen.gba app/src/androidTest/assets/leafgreen.gba
```

Open the project in Android Studio. The first sync will take a while because CMake will configure mGBA.

### Phase 0 verification

```bash
./gradlew connectedDebugAndroidTest
```

Both tests in `Phase0EmulatorEmbedTest` must pass:
- `loadsRomAndRunsFrames` — ROM loads, 600 frames execute without crash, framebuffer is non-zero
- `framebufferHashIsDeterministic` — two independent 600-frame runs produce byte-identical framebuffers

If those pass, Phase 0 is complete and Phase 1 (playable UI) can begin.

### Layout

```
app/
  src/main/cpp/         # JNI bridge + native gate logic
    CMakeLists.txt      # builds libmgba.a (static) + libpoketrek.so (shared)
    jni_bridge.cpp      # loadRom, runFrame, getFramebuffer, ...
    movement_gate.{h,cpp}  # input filter (Phase 3b)
  src/main/java/com/poketrek/
    EmulatorActivity.kt    # PokéTrek harness (emulator + step-counter)
    emu/NativeEmulator.kt
    moneo/                 # Moneo: SRS, corpus, review UI, correction reporting
  src/androidTest/java/com/poketrek/emu/
    Phase0EmulatorEmbedTest.kt
tools/moneo/             # Korean text extraction + glyph-map pipeline
third_party/mgba/        # submodule, pinned tag (see .gitmodules)
```

> **Note on the `com.poketrek` package id**: the Android package is still
> `com.poketrek` for historical reasons (PokéTrek pre-dates Moneo). The
> launcher icon, settings sheet, and notifications all read "Moneo" — the
> package id is just the internal Android identifier and is not
> user-visible. Renaming it would orphan everyone's existing install +
> SRS progress.

## ROM handling

ROM files are never committed to this repository. `*.gba` is in `.gitignore`. The runtime app uses Android's Storage Access Framework so the user picks their own ROM at runtime.

## Korean ROM (2024 fan-translation)

Moneo is built around the **2024 Korean fan-translation** of LeafGreen (CRC32 `0x4A38A8CB`). That ROM is produced by applying an xdelta patch to a Japanese FRLG base — **not** the English one. The fan-translation team built on the Japanese binary because the JP RE community had already done the tile/font work; the filename `leafgreen_J-K_2024.gba` encodes this: **J**apanese base, **K**orean-patched.

The patch and the JP base ROM are both **third-party works**: we don't ship either. You supply your own legally-obtained JP LeafGreen dump, then run the included patcher locally.

### Quick setup

1. Acquire a Japanese FRLG 1.0 ROM yourself (MD5 must match `138a71a5be83f3f3d7af3d31916a5fc7` — the patcher will warn you if it doesn't). Moneo does not distribute it.
2. Fetch the patch zip from the team's [hangulogame.com page](https://www.hangulogame.com/patch/gba/844/) (or [mirror](https://drive.google.com/uc?export=download&id=1PtJ7YplZBdN8Yvb3cw-w9hrt-sT2trPt)) and extract `leafgreen_J-K.xdelta` into `tools/moneo/rom_swap/`. See [`tools/moneo/rom_swap/README.md`](tools/moneo/rom_swap/README.md#whats-here) for a one-liner that pulls the zip and renames the three GBA-series patches.
3. Apply:
   ```bash
   source .venv-moneo/bin/activate   # or your preferred venv
   pip install xdelta3
   python3 tools/moneo/rom_swap/apply_patch.py /path/to/leafgreen_japan.gba
   # → writes tools/moneo/rom_swap/leafgreen_J-K_2024.gba
   ```
4. Inside the app, use **Settings → Add ROM** and pick the patched `.gba`. Moneo's `RomIdentity` will recognize CRC32 `0x4A38A8CB` and enable Korean-specific flashcard features.

Full workflow (offset re-derivation, diagnostic script, what to expect after patching) is documented in [`tools/moneo/rom_swap/README.md`](tools/moneo/rom_swap/README.md).

### Credits

The 2024-02-29 Korean fan-translation patch is the work of:

- **명군** (lead)
- tony
- koi
- 돌아온달토끼

Patch distribution + discussion:

- [hangulogame.com — Pokémon FireRed/LeafGreen Korean Fan Translation, v20240229](https://www.hangulogame.com/patch/gba/844/) — canonical patch page (English/Korean release notes, version history)
- [DCInside Nintendo mini-gallery release thread, post 2515975](https://gall.dcinside.com/mgallery/board/view/?id=game_nintendo&no=2515975) — original release announcement + community Q&A

Moneo's pipeline (corpus mining, glyph map, in-app flashcards) is built on top of their translation work. None of this would exist without their effort. If you find issues with the Korean text in Moneo's flashcards, those are on us — please report them via the **✎ Report** button in the review screen, which opens a [pre-filled GitHub Issue](https://github.com/Stan-Stani/moneo/issues/new?template=korean-correction.yml).

The US Rev 1 English LeafGreen (CRC32 `0xDAFFECEC`) is also supported as a non-localized variant; the step-gating logic (PokéTrek) works against either ROM, but the Korean flashcard surface is dormant on the English ROM.
