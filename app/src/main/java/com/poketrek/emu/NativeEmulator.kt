package com.poketrek.emu

/**
 * Kotlin handle to the embedded mGBA core. All methods JNI into libpoketrek.so.
 *
 * Phase 0 surface only — input, audio, save state, and RAM reads will be added
 * in later phases.
 */
class NativeEmulator {
    init {
        System.loadLibrary("poketrek")
    }

    /** Loads a ROM from a byte array. Replaces any previously loaded ROM. */
    external fun loadRom(romBytes: ByteArray): Boolean

    /** Runs a single GBA frame. Caller is responsible for ~60 Hz pacing. */
    external fun runFrame()

    /** Returns the most recent framebuffer as RGBA8888, 240x160 = 153,600 bytes. */
    external fun getFramebuffer(): ByteArray

    /** FNV-1a 64-bit hash of the framebuffer — used by Phase 0 determinism test. */
    external fun getFramebufferHash(): Long

    /** Releases the native emulator instance. */
    external fun destroy()
}
