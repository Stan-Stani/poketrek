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

    /**
     * Sets the GBA key bitmask (active-high). Bits per the GBA KEYINPUT layout:
     * 0=A, 1=B, 2=Select, 3=Start, 4=Right, 5=Left, 6=Up, 7=Down, 8=R, 9=L.
     */
    external fun setKeys(keys: Int)

    /**
     * Copies the current framebuffer into a direct [java.nio.ByteBuffer] of at
     * least 240*160*4 bytes. Returns true on success. Avoids per-frame allocs.
     */
    external fun writeFramebuffer(buffer: java.nio.ByteBuffer): Boolean

    /** Reads one byte from emulated GBA address [addr]. Returns 0..255. */
    external fun busRead8(addr: Int): Int

    /** Reads a little-endian 16-bit halfword. Returns 0..65535. */
    external fun busRead16(addr: Int): Int

    /** Reads a little-endian 32-bit word. Sign-extended into Java Int. */
    external fun busRead32(addr: Int): Int

    /** Serializes the emulator state into a byte array. Returns null on failure. */
    external fun saveState(): ByteArray?

    /** Restores emulator state from a previously-saved byte array. */
    external fun loadState(data: ByteArray): Boolean
}

/** GBA key bits matching mGBA's setKeys mask. */
object GbaKey {
    const val A      = 1 shl 0
    const val B      = 1 shl 1
    const val SELECT = 1 shl 2
    const val START  = 1 shl 3
    const val RIGHT  = 1 shl 4
    const val LEFT   = 1 shl 5
    const val UP     = 1 shl 6
    const val DOWN   = 1 shl 7
    const val R      = 1 shl 8
    const val L      = 1 shl 9
}
