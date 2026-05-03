package com.poketrek.emu

/**
 * Discovers the SaveBlock1 pointer location for an uncalibrated ROM.
 *
 * The user takes a baseline EWRAM snapshot, walks exactly one tile in the
 * overworld, and we capture a second snapshot. We then:
 *   1. Find EWRAM halfwords whose value changed by exactly ±1 — the
 *      signature of a single-tile coordinate update at SaveBlock1+0 (X)
 *      or +2 (Y).
 *   2. For each candidate, the SaveBlock1 base address is either the
 *      halfword's address or that address minus 2. Build the union.
 *   3. Scan IWRAM for any 32-bit word whose value equals one of those
 *      candidate base addresses. The IWRAM offset of that word is the
 *      target — for US Rev 1 it's 0x03005008.
 *
 * Pure Kotlin so it can be unit-tested with a fake [BusReader] without an
 * Android device.
 */
object RomCalibrator {
    const val EWRAM_BASE = 0x02000000
    const val EWRAM_SIZE = 0x40000  // 256 KB
    const val IWRAM_BASE = 0x03000000
    const val IWRAM_SIZE = 0x8000   // 32 KB

    /** Tiny bulk-read surface so the calibrator is JVM-testable. */
    interface BusReader {
        fun readBytes(addr: Int, length: Int): ByteArray?
    }

    sealed class Result {
        /** [saveBlock1PtrAddr] holds [saveBlock1Base] in the live emulator. */
        data class Ok(val saveBlock1PtrAddr: Int, val saveBlock1Base: Int) : Result()
        /** No EWRAM halfword changed by exactly ±1 — user didn't actually move? */
        object NoChangedHalfword : Result()
        /** Too many ±1-delta halfwords to disambiguate. Caller should retry. */
        data class TooManyChangedHalfwords(val count: Int) : Result()
        /** Found candidate coords but no IWRAM pointer references them. */
        object NoPointerFound : Result()
        /** Multiple distinct IWRAM pointers match; calibration is ambiguous. */
        data class MultiplePointers(val addrs: List<Int>) : Result()
        /** Bus read failed (no ROM loaded, etc). */
        object ReadFailed : Result()
    }

    fun snapshotEwram(reader: BusReader): ByteArray? =
        reader.readBytes(EWRAM_BASE, EWRAM_SIZE)

    /**
     * Returns EWRAM addresses of halfwords whose value changed between the
     * two snapshots by exactly ±1 — the signature of a single-tile player
     * step. Tightening from "any change" filters out noise from RNGs,
     * frame counters, sound mixers, etc.
     */
    fun findChangedHalfwords(
        before: ByteArray,
        after: ByteArray,
        baseAddr: Int = EWRAM_BASE,
    ): List<Int> {
        require(before.size == after.size) { "snapshots differ in size" }
        require(before.size % 2 == 0) { "size must be even" }
        val out = mutableListOf<Int>()
        var i = 0
        while (i < before.size) {
            val b = readU16Le(before, i)
            val a = readU16Le(after, i)
            val delta = a - b
            if (delta == 1 || delta == -1) {
                out.add(baseAddr + i)
            }
            i += 2
        }
        return out
    }

    /**
     * Returns IWRAM addresses (the pointer-holding cells) whose 32-bit
     * value equals any element of [candidates]. Map value is the pointer
     * value itself, useful for disambiguating which X/Y halfword pinned
     * the match.
     */
    fun findPointersTo(
        iwram: ByteArray,
        candidates: Set<Int>,
        baseAddr: Int = IWRAM_BASE,
    ): Map<Int, Int> {
        require(iwram.size % 4 == 0) { "iwram size must be 4-aligned" }
        val out = mutableMapOf<Int, Int>()
        var i = 0
        while (i + 4 <= iwram.size) {
            val v = readU32Le(iwram, i)
            if (v in candidates) {
                out[baseAddr + i] = v
            }
            i += 4
        }
        return out
    }

    /**
     * Full calibration pass given a [before] EWRAM snapshot taken before
     * the user walked one tile. Reads "after" EWRAM and IWRAM via
     * [reader], diffs, and returns either a unique answer or a typed
     * failure the UI can surface.
     */
    fun calibrate(reader: BusReader, before: ByteArray): Result {
        val after = snapshotEwram(reader) ?: return Result.ReadFailed
        if (after.size != before.size) return Result.ReadFailed
        val changed = findChangedHalfwords(before, after)
        if (changed.isEmpty()) return Result.NoChangedHalfword
        // 64 picked to be generous — with proper "stand still" baseline
        // the practical count should be single digits.
        if (changed.size > 64) return Result.TooManyChangedHalfwords(changed.size)

        val baseCandidates = mutableSetOf<Int>()
        for (a in changed) {
            baseCandidates.add(a)
            baseCandidates.add(a - 2)
        }
        val iwram = reader.readBytes(IWRAM_BASE, IWRAM_SIZE) ?: return Result.ReadFailed
        val matches = findPointersTo(iwram, baseCandidates)
        return when {
            matches.isEmpty() -> Result.NoPointerFound
            matches.size > 1 -> Result.MultiplePointers(matches.keys.sorted())
            else -> {
                val (ptrAddr, base) = matches.entries.first()
                Result.Ok(saveBlock1PtrAddr = ptrAddr, saveBlock1Base = base)
            }
        }
    }

    private fun readU16Le(b: ByteArray, i: Int): Int =
        (b[i].toInt() and 0xff) or ((b[i + 1].toInt() and 0xff) shl 8)

    private fun readU32Le(b: ByteArray, i: Int): Int =
        (b[i].toInt() and 0xff) or
            ((b[i + 1].toInt() and 0xff) shl 8) or
            ((b[i + 2].toInt() and 0xff) shl 16) or
            ((b[i + 3].toInt() and 0xff) shl 24)
}
