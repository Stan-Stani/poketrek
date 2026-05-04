package com.poketrek.moneo.corpus

import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.io.File
import java.util.zip.CRC32

/**
 * Empirical Korean text capture from a running emulator's EWRAM.
 *
 * **Why this exists.** The Korean LeafGreen ROM dump we have is wrapped in
 * an in-ROM self-decryption stub (header title is `YJencrypted`). The ROM
 * boots fine inside mGBA — its own boot code decrypts code/data at runtime —
 * but a static byte-pattern rip of the cartridge image returns scrambled
 * bytes. The fix is to capture text from EWRAM (and WRAM) at runtime, where
 * the data is plaintext.
 *
 * **What this does.** Every [SAMPLE_INTERVAL_MS] milliseconds (driven by an
 * internal coroutine) we read EWRAM (`0x02000000` + 256 KiB) and look for
 * *contiguous runs of changed bytes* compared to the previous sample. A run
 * that
 *  (a) lasts at least [MIN_RUN_BYTES] bytes,
 *  (b) is bounded by zero/0xFF terminators on at least one side, and
 *  (c) hashes to a value we haven't seen recently
 * is appended (with its address and a CRC32) to a capture file in
 * `filesDir/moneo/capture.bin`.
 *
 * **Encoding.** Captured runs are raw bytes. We do not yet know the Gen-3
 * Korean charmap; the offline dev tool [com.poketrek.moneo.corpus.CharmapTool]
 * derives it incrementally by overlaying the framebuffer's font tiles.
 *
 * Capture is opt-in (the user toggles it from the Moneo settings) and
 * does nothing when disabled.
 */
class RamCapture(
    private val reader: BusReader,
    private val outputDir: File,
) {

    /** Minimal RAM-read interface so Moneo doesn't import the emulator's NativeEmulator. */
    fun interface BusReader {
        /** Returns null if no ROM is loaded or the read fails. */
        fun readBytes(addr: Int, length: Int): ByteArray?
    }

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private var pollJob: Job? = null

    private val _enabled = MutableStateFlow(false)
    val enabled: StateFlow<Boolean> = _enabled.asStateFlow()

    private val _runsCaptured = MutableStateFlow(0)
    val runsCaptured: StateFlow<Int> = _runsCaptured.asStateFlow()

    private var lastSnapshot: ByteArray? = null
    /** Recent CRC32s of captured runs, kept to dedupe. */
    private val recentDigests = ArrayDeque<Long>()
    private val recentDigestSet = HashSet<Long>()

    fun setEnabled(value: Boolean) {
        if (value == _enabled.value) return
        _enabled.value = value
        if (value) {
            outputDir.mkdirs()
            pollJob = scope.launch {
                while (isActive && _enabled.value) {
                    runCatching { sampleOnce() }
                        .onFailure { Log.w(TAG, "sample failed", it) }
                    delay(SAMPLE_INTERVAL_MS)
                }
            }
        } else {
            pollJob?.cancel()
            pollJob = null
            // Drop the snapshot so re-enabling doesn't emit "everything changed
            // since you last had it on" as one giant blob.
            lastSnapshot = null
        }
    }

    private fun sampleOnce() {
        val current = reader.readBytes(EWRAM_BASE, EWRAM_SIZE) ?: return
        val previous = lastSnapshot
        lastSnapshot = current
        if (previous == null || previous.size != current.size) return
        captureRuns(previous, current)
    }

    private fun captureRuns(prev: ByteArray, cur: ByteArray) {
        val len = cur.size
        var i = 0
        var emitted = 0
        while (i < len) {
            if (prev[i] == cur[i]) { i++; continue }
            val runStart = i
            while (i < len && prev[i] != cur[i]) i++
            val runEnd = i
            val runLen = runEnd - runStart
            if (runLen < MIN_RUN_BYTES) continue
            // Trim leading/trailing terminator/padding bytes.
            var s = runStart
            var e = runEnd
            while (s < e && (cur[s] == 0x00.toByte() || cur[s] == 0xFF.toByte())) s++
            while (e > s && (cur[e - 1] == 0x00.toByte() || cur[e - 1] == 0xFF.toByte())) e--
            if (e - s < MIN_RUN_BYTES) continue
            val bytes = cur.copyOfRange(s, e)
            val digest = CRC32().apply { update(bytes) }.value
            if (!seenRecently(digest)) {
                appendCapture(EWRAM_BASE + s, bytes, digest)
                emitted++
            }
        }
        if (emitted > 0) _runsCaptured.value = _runsCaptured.value + emitted
    }

    private fun seenRecently(digest: Long): Boolean {
        if (digest in recentDigestSet) return true
        recentDigests.addLast(digest)
        recentDigestSet.add(digest)
        if (recentDigests.size > MAX_RECENT_DIGESTS) {
            val dropped = recentDigests.removeFirst()
            recentDigestSet.remove(dropped)
        }
        return false
    }

    private fun appendCapture(addr: Int, bytes: ByteArray, digest: Long) {
        val file = File(outputDir, FILE_NAME)
        try {
            val isNew = !file.exists()
            // Per-record format (little-endian):
            //   [first record only] u32 magic = 'KCAP'
            //   u32 timestamp_ms_low
            //   u32 addr
            //   u32 length
            //   u32 crc32
            //   bytes ...
            file.appendBytes(headerIfNew(isNew))
            val ts = System.currentTimeMillis()
            file.appendBytes(le32(ts.toInt()))
            file.appendBytes(le32(addr))
            file.appendBytes(le32(bytes.size))
            file.appendBytes(le32(digest.toInt()))
            file.appendBytes(bytes)
        } catch (e: Exception) {
            Log.w(TAG, "Capture write failed", e)
        }
    }

    private fun headerIfNew(isNew: Boolean): ByteArray =
        if (isNew) MAGIC else ByteArray(0)

    private fun le32(v: Int): ByteArray = byteArrayOf(
        (v and 0xFF).toByte(),
        ((v ushr 8) and 0xFF).toByte(),
        ((v ushr 16) and 0xFF).toByte(),
        ((v ushr 24) and 0xFF).toByte(),
    )

    /** File location for export. */
    fun captureFile(): File = File(outputDir, FILE_NAME)

    fun captureSizeBytes(): Long = captureFile().length()

    fun resetCapture() {
        captureFile().delete()
        recentDigests.clear()
        recentDigestSet.clear()
        lastSnapshot = null
        _runsCaptured.value = 0
    }

    companion object {
        private const val TAG = "RamCapture"
        private const val FILE_NAME = "capture.bin"

        /** GBA EWRAM base / size. Plenty large for any single dialog buffer. */
        const val EWRAM_BASE: Int = 0x02000000
        const val EWRAM_SIZE: Int = 256 * 1024

        /** Poll cadence (ms). 500 ≈ twice/second; tradeoff against CPU. */
        const val SAMPLE_INTERVAL_MS: Long = 500L

        /** Runs shorter than this are noise (timers, RNG, sprite scratch). */
        const val MIN_RUN_BYTES: Int = 12

        /** Dedupe window. Keeps memory bounded. */
        const val MAX_RECENT_DIGESTS: Int = 1024

        private val MAGIC: ByteArray = byteArrayOf('K'.code.toByte(), 'C'.code.toByte(), 'A'.code.toByte(), 'P'.code.toByte())
    }
}
