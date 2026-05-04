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

    private var lastCharblock0Hash: Int = 0

    fun setEnabled(value: Boolean) {
        if (value == _enabled.value) return
        _enabled.value = value
        if (value) {
            outputDir.mkdirs()
            pollJob = scope.launch {
                while (isActive && _enabled.value) {
                    runCatching { sampleOnce() }
                        .onFailure { Log.w(TAG, "sample failed", it) }
                    runCatching { snapshotCharblockIfChanged() }
                        .onFailure { Log.w(TAG, "charblock snapshot failed", it) }
                    delay(SAMPLE_INTERVAL_MS)
                }
            }
        } else {
            pollJob?.cancel()
            pollJob = null
            lastSnapshot = null
        }
    }

    /** Save charblock0 whenever its content changes significantly (≥32 tiles differ). */
    private fun snapshotCharblockIfChanged() {
        val cb0 = reader.readBytes(0x06000000, 16384) ?: return
        val hash = cb0.contentHashCode()
        if (hash == lastCharblock0Hash) return
        // Count non-zero tiles
        val nonZeroTiles = (0 until 512).count { t ->
            cb0.slice(t*32 until t*32+32).any { it != 0.toByte() }
        }
        // Only save if it looks like a font/text charblock (moderate number of non-zero tiles)
        if (nonZeroTiles in 50..400) {
            val ts = System.currentTimeMillis()
            val cbFile = File(outputDir, "charblock0_snap_${ts}.bin")
            cbFile.writeBytes(cb0)
            Log.i("MoneoProbe", "CharblockSnap: nonzeroTiles=$nonZeroTiles saved=${cbFile.name}")
        }
        lastCharblock0Hash = hash
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

    /**
     * Synchronously read gStringVar1–4 from EWRAM and log to Logcat with tag "MoneoProbe".
     * Call from any thread; does its own bus read.
     *
     * Gen3 string buffer addresses (identical in US and KO LeafGreen):
     *   gStringVar1 = 0x020370E4
     *   gStringVar2 = 0x020371E8
     *   gStringVar3 = 0x020372EC
     *   gStringVar4 = 0x020373F0
     *
     * Returns a map of varName → raw hex (null if the read failed).
     */
    fun probeTextBuffers(): Map<String, String?> {
        val bases = mapOf(
            "gStringVar1" to 0x020370E4,
            "gStringVar2" to 0x020371E8,
            "gStringVar3" to 0x020372EC,
            "gStringVar4" to 0x020373F0,
        )
        val result = LinkedHashMap<String, String?>()
        for ((name, addr) in bases) {
            val bytes = reader.readBytes(addr, 64) ?: continue
            val hex = bytes.joinToString(" ") { "%02x".format(it) }
            Log.i("MoneoProbe", "$name @ 0x${addr.toString(16)} = $hex")
            result[name] = hex
        }

        // Scan EWRAM for ROM pointers (values in 0x08000000–0x09FFFFFF).
        // The Gen3 text printer stores the current message text pointer in a struct
        // somewhere in EWRAM. By finding ROM pointers we can read the raw script bytes
        // and observe the byte encoding for each Korean character on screen.
        val ewramBase = 0x02000000
        val ewramSize = 256 * 1024
        val ewram = reader.readBytes(ewramBase, ewramSize) ?: ByteArray(0)
        val romPtrs = mutableListOf<Pair<Int, Int>>() // (ewram_offset, rom_addr)
        if (ewram.isNotEmpty()) {
            var i = 0
            while (i + 3 < ewram.size) {
                val lo = ewram[i].toInt() and 0xFF
                val b1 = ewram[i+1].toInt() and 0xFF
                val b2 = ewram[i+2].toInt() and 0xFF
                val hi = ewram[i+3].toInt() and 0xFF
                // ROM address range: 0x08000000–0x09FFFFFF (hi byte = 0x08 or 0x09)
                if (hi == 0x08 || hi == 0x09) {
                    val romAddr = lo or (b1 shl 8) or (b2 shl 16) or (hi shl 24)
                    romPtrs.add(Pair(ewramBase + i, romAddr))
                }
                i += 4
            }
        }
        Log.i("MoneoProbe", "Found ${romPtrs.size} ROM pointers in EWRAM")
        // For each unique ROM pointer, read 32 bytes and log (capped at 50 ptrs)
        val seenRomAddrs = mutableSetOf<Int>()
        var ptrCount = 0
        for ((ewramOff, romAddr) in romPtrs) {
            if (!seenRomAddrs.add(romAddr)) continue
            if (ptrCount++ >= 50) break
            val romBytes = reader.readBytes(romAddr, 32) ?: continue
            val hex = romBytes.joinToString(" ") { "%02x".format(it) }
            Log.i("MoneoProbe", "ROM_PTR @ ewram+0x${(ewramOff - ewramBase).toString(16)} -> 0x${romAddr.toString(16)} = $hex")
        }
        result["rom_ptrs"] = "${romPtrs.size} found"

        // Scan IWRAM (0x03000000–0x03007FFF) for ROM text pointers.
        // Gen3 text printer state lives in IWRAM; finding ROM pointers there gives
        // us the active message text address.
        val iwramBase = 0x03000000
        val iwram = reader.readBytes(iwramBase, 32 * 1024) ?: ByteArray(0)
        if (iwram.isNotEmpty()) {
            var i = 0
            while (i + 3 < iwram.size) {
                val lo = iwram[i].toInt() and 0xFF
                val b1 = iwram[i+1].toInt() and 0xFF
                val b2 = iwram[i+2].toInt() and 0xFF
                val hi = iwram[i+3].toInt() and 0xFF
                if (hi == 0x08 || hi == 0x09) {
                    val romAddr = lo or (b1 shl 8) or (b2 shl 16) or (hi shl 24)
                    val strBytes = reader.readBytes(romAddr, 48) ?: continue
                    // Look for text: bytes in 0x01-0xFE range, not all 0xFF or 0x00
                    val textLike = strBytes.count { (it.toInt() and 0xFF) in 0x01..0xFE }
                    if (textLike >= 8) {
                        val hex = strBytes.joinToString(" ") { "%02x".format(it) }
                        Log.i("MoneoProbe", "IWRAM_PTR+0x${i.toString(16)} -> 0x${romAddr.toString(16)} textLike=$textLike | $hex")
                    }
                }
                i += 4
            }
        }

        // Scan all 32 VRAM screenblocks (0x06000000–0x0600FFFF, each 2KB)
        // to find which BG has non-zero tile indices (= text on screen).
        val vramBgBase = 0x06000000
        val sb = 2048 // bytes per screenblock
        val dumpFile = File(outputDir, "vram_probe.bin")
        val dumpOut = dumpFile.outputStream().buffered()
        try {
            for (i in 0 until 32) {
                val addr = vramBgBase + i * sb
                val bytes = reader.readBytes(addr, sb) ?: continue
                val nonZero = bytes.count { it != 0.toByte() }
                val preview = bytes.take(64).joinToString(" ") { "%02x".format(it) }
                Log.i("MoneoProbe", "VRAM_SB$i (0x${addr.toString(16)}) nonzero=$nonZero = $preview")
                result["VRAM_SB$i"] = "nonzero=$nonZero"
                // Write header: [i:u8, addr:u32LE, nonzero:u32LE, 2048 bytes]
                dumpOut.write(byteArrayOf(i.toByte()))
                dumpOut.write(le32(addr))
                dumpOut.write(le32(nonZero))
                dumpOut.write(bytes)
            }
        } finally {
            dumpOut.close()
        }
        Log.i("MoneoProbe", "VRAM dump written to ${dumpFile.absolutePath}")
        result["vram_dump"] = dumpFile.absolutePath

        // Dump charblock 0 (0x06000000, 16KB) — contains all glyph pixel data
        val charblock0 = reader.readBytes(0x06000000, 16384)
        if (charblock0 != null) {
            val cbFile = File(outputDir, "charblock0.bin")
            cbFile.writeBytes(charblock0)
            Log.i("MoneoProbe", "Charblock0 dump written to ${cbFile.absolutePath}")
            result["charblock0_dump"] = cbFile.absolutePath
        }

        // Try ROM bus read — if ROM is decrypted at runtime, 0x08000000 returns plaintext
        val romHeader = reader.readBytes(0x08000000, 256)
        if (romHeader != null) {
            val romHex = romHeader.take(64).joinToString(" ") { "%02x".format(it) }
            Log.i("MoneoProbe", "ROM bus @ 0x8000000 (first 64B) = $romHex")
            result["rom_header"] = romHex
            // Search for "GAMEFREAK" or "POKEMON" ASCII to confirm decryption
            val ascii = romHeader.map { if (it in 0x20..0x7E) it.toInt().toChar() else '.' }.joinToString("")
            Log.i("MoneoProbe", "ROM header ASCII = $ascii")
        }

        return result
    }

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
