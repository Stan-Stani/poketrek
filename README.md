# PokéTrek

An Android app that step-gates Pokémon LeafGreen overworld walking. Real-world steps (read from the phone's hardware step counter) become a movement budget; on-foot tile movement in the overworld consumes that budget.

The full design lives at `~/.claude/plans/i-would-like-to-inherited-papert.md`. Read that first.

## Status

**Phase 0** — emulator embed scaffolded; not yet validated on-device.

## Prerequisites

- macOS / Linux
- [Android Studio](https://developer.android.com/studio) (Ladybug 2024.2.1 or newer recommended)
- Android NDK `27.2.12479018` (install via Android Studio → SDK Manager → SDK Tools)
- CMake `3.22.1+` (also via SDK Manager)
- A device or emulator running Android 8.0+ (API 26). For step-counter testing, a physical device with a hardware pedometer is required — the Android Emulator does not expose `TYPE_STEP_COUNTER`.

## First-time setup

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

## Phase 0 verification

```bash
./gradlew connectedDebugAndroidTest
```

Both tests in `Phase0EmulatorEmbedTest` must pass:
- `loadsRomAndRunsFrames` — ROM loads, 600 frames execute without crash, framebuffer is non-zero
- `framebufferHashIsDeterministic` — two independent 600-frame runs produce byte-identical framebuffers

If those pass, Phase 0 is complete and Phase 1 (playable UI) can begin.

## Layout

```
app/
  src/main/cpp/         # JNI bridge + native gate logic
    CMakeLists.txt      # builds libmgba.a (static) + libpoketrek.so (shared)
    jni_bridge.cpp      # loadRom, runFrame, getFramebuffer, ...
    movement_gate.{h,cpp}  # input filter (Phase 3b)
  src/main/java/com/poketrek/
    EmulatorActivity.kt
    emu/NativeEmulator.kt
  src/androidTest/java/com/poketrek/emu/
    Phase0EmulatorEmbedTest.kt
third_party/mgba/        # submodule, pinned tag (see .gitmodules)
```

## ROM handling

ROM files are never committed to this repository. `*.gba` is in `.gitignore`. The runtime app uses Android's Storage Access Framework so the user picks their own ROM at runtime.

## Korean ROM (2024 fan-translation)

The flashcard side of the app (moneo) is built around the **2024 Korean fan-translation** of LeafGreen (CRC32 `0x4A38A8CB`). That ROM is produced by applying an xdelta patch to a Japanese FRLG base — **not** the English one. The fan-translation team built on the Japanese binary because the JP RE community had already done the tile/font work; the filename `leafgreen_J-K_2024.gba` encodes this: **J**apanese base, **K**orean-patched.

The patch and the JP base ROM are both **third-party works**: we don't ship either. You supply your own legally-obtained JP LeafGreen dump, then run the included patcher locally.

### Quick setup

1. Acquire a Japanese FRLG 1.0 ROM yourself (MD5 must match `138a71a5be83f3f3d7af3d31916a5fc7` — the patcher will warn you if it doesn't). PokéTrek does not distribute it.
2. Fetch the patch zip (link in `tools/moneo/rom_swap/README.md`) and extract `leafgreen_J-K.xdelta` into `tools/moneo/rom_swap/`.
3. Apply:
   ```bash
   source .venv-moneo/bin/activate   # or your preferred venv
   pip install xdelta3
   python3 tools/moneo/rom_swap/apply_patch.py /path/to/leafgreen_japan.gba
   # → writes tools/moneo/rom_swap/leafgreen_J-K_2024.gba
   ```
4. Inside the app, use **Settings → Add ROM** and pick the patched `.gba`. PokéTrek's `RomIdentity` will recognize CRC32 `0x4A38A8CB` and enable Korean-specific moneo features.

Full workflow (offset re-derivation, diagnostic script, what to expect after patching) is documented in [`tools/moneo/rom_swap/README.md`](tools/moneo/rom_swap/README.md).

### Credits

The 2024-02-29 Korean fan-translation patch is the work of:

- **명군** (lead)
- tony
- koi
- 돌아온달토끼

Discussion threads where the patch was distributed and refined:

- DCInside `mgallery/board/view/?id=game_nintendo&no=2515975` — the Nintendo mini-gallery release thread
- hangulogame.com post 844

PokéTrek's moneo pipeline (corpus mining, glyph map, in-app flashcards) is built on top of their translation work. None of this would exist without their effort. If you find issues with the Korean text in moneo's flashcards, those are on us — please report them via the **✎ Report** button in the review screen, which opens a [pre-filled GitHub Issue](https://github.com/Stan-Stani/poketrek/issues/new?template=korean-correction.yml).

The US Rev 1 English LeafGreen (CRC32 `0xDAFFECEC`) is also supported as a non-localized variant; the step-gating logic works against either ROM.
