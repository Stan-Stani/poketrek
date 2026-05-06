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
