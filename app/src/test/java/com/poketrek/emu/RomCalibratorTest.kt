package com.poketrek.emu

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class RomCalibratorTest {

    /**
     * Synthetic GBA RAM laid out like a real session: SaveBlock1 lives at
     * some EWRAM address, IWRAM holds a pointer to it. Used to drive the
     * calibrator end-to-end without a native emulator.
     */
    private class FakeBus(
        ewram: ByteArray = ByteArray(RomCalibrator.EWRAM_SIZE),
        iwram: ByteArray = ByteArray(RomCalibrator.IWRAM_SIZE),
    ) : RomCalibrator.BusReader {
        val ewram = ewram
        val iwram = iwram

        override fun readBytes(addr: Int, length: Int): ByteArray? {
            return when {
                addr == RomCalibrator.EWRAM_BASE && length == RomCalibrator.EWRAM_SIZE ->
                    ewram.copyOf()
                addr == RomCalibrator.IWRAM_BASE && length == RomCalibrator.IWRAM_SIZE ->
                    iwram.copyOf()
                else -> null
            }
        }
    }

    private fun writeU16Le(buf: ByteArray, off: Int, value: Int) {
        buf[off] = (value and 0xff).toByte()
        buf[off + 1] = ((value ushr 8) and 0xff).toByte()
    }

    private fun writeU32Le(buf: ByteArray, off: Int, value: Int) {
        buf[off] = (value and 0xff).toByte()
        buf[off + 1] = ((value ushr 8) and 0xff).toByte()
        buf[off + 2] = ((value ushr 16) and 0xff).toByte()
        buf[off + 3] = ((value ushr 24) and 0xff).toByte()
    }

    @Test
    fun calibrate_unique_match_returns_ptr_and_base() {
        // Mirror the US Rev 1 layout: SaveBlock1 base at 0x02025734,
        // pointer to it stored in IWRAM at 0x03005008.
        val sb1Base = 0x02025734
        val ptrAddr = 0x03005008

        val bus = FakeBus()
        // Initial: X=10, Y=20 at SaveBlock1+0/+2.
        val sb1Off = sb1Base - RomCalibrator.EWRAM_BASE
        writeU16Le(bus.ewram, sb1Off + 0, 10)
        writeU16Le(bus.ewram, sb1Off + 2, 20)
        // Pointer in IWRAM points at SaveBlock1 base.
        writeU32Le(bus.iwram, ptrAddr - RomCalibrator.IWRAM_BASE, sb1Base)

        val before = bus.readBytes(RomCalibrator.EWRAM_BASE, RomCalibrator.EWRAM_SIZE)!!
        // Player walks one tile east: X 10 → 11.
        writeU16Le(bus.ewram, sb1Off + 0, 11)

        val result = RomCalibrator.calibrate(bus, before)
        assertTrue("expected Ok, got $result", result is RomCalibrator.Result.Ok)
        result as RomCalibrator.Result.Ok
        assertEquals(ptrAddr, result.saveBlock1PtrAddr)
        assertEquals(sb1Base, result.saveBlock1Base)
    }

    @Test
    fun calibrate_y_step_also_works() {
        val sb1Base = 0x02030100
        val ptrAddr = 0x03004ff0

        val bus = FakeBus()
        val sb1Off = sb1Base - RomCalibrator.EWRAM_BASE
        writeU16Le(bus.ewram, sb1Off + 0, 5)
        writeU16Le(bus.ewram, sb1Off + 2, 7)
        writeU32Le(bus.iwram, ptrAddr - RomCalibrator.IWRAM_BASE, sb1Base)

        val before = bus.readBytes(RomCalibrator.EWRAM_BASE, RomCalibrator.EWRAM_SIZE)!!
        // Y goes from 7 → 6 (step north).
        writeU16Le(bus.ewram, sb1Off + 2, 6)

        val result = RomCalibrator.calibrate(bus, before)
        assertTrue(result is RomCalibrator.Result.Ok)
        assertEquals(ptrAddr, (result as RomCalibrator.Result.Ok).saveBlock1PtrAddr)
        assertEquals(sb1Base, result.saveBlock1Base)
    }

    @Test
    fun calibrate_no_movement_returns_NoChangedHalfword() {
        val bus = FakeBus()
        val before = bus.readBytes(RomCalibrator.EWRAM_BASE, RomCalibrator.EWRAM_SIZE)!!
        // No EWRAM mutation between snapshots.
        val result = RomCalibrator.calibrate(bus, before)
        assertEquals(RomCalibrator.Result.NoChangedHalfword, result)
    }

    @Test
    fun calibrate_no_pointer_in_iwram_returns_NoPointerFound() {
        val bus = FakeBus()
        // Mutate a halfword by ±1 but never store a pointer to it.
        val sb1Off = 0x10000
        writeU16Le(bus.ewram, sb1Off, 100)
        val before = bus.readBytes(RomCalibrator.EWRAM_BASE, RomCalibrator.EWRAM_SIZE)!!
        writeU16Le(bus.ewram, sb1Off, 101)

        val result = RomCalibrator.calibrate(bus, before)
        assertEquals(RomCalibrator.Result.NoPointerFound, result)
    }

    @Test
    fun calibrate_two_distinct_pointers_returns_MultiplePointers() {
        val sb1Base = 0x02025734
        val bus = FakeBus()
        val sb1Off = sb1Base - RomCalibrator.EWRAM_BASE
        writeU16Le(bus.ewram, sb1Off + 0, 10)
        // Two IWRAM cells both hold the same SaveBlock1 base.
        writeU32Le(bus.iwram, 0x4000, sb1Base)
        writeU32Le(bus.iwram, 0x5008, sb1Base)
        val before = bus.readBytes(RomCalibrator.EWRAM_BASE, RomCalibrator.EWRAM_SIZE)!!
        writeU16Le(bus.ewram, sb1Off + 0, 11)

        val result = RomCalibrator.calibrate(bus, before)
        assertTrue("expected Multi, got $result", result is RomCalibrator.Result.MultiplePointers)
        result as RomCalibrator.Result.MultiplePointers
        assertEquals(listOf(0x03004000, 0x03005008), result.addrs)
    }

    @Test
    fun calibrate_large_delta_is_ignored() {
        // Coordinate jumps of more than 1 (warp, fly, scripted move) should
        // not be considered a "step." Verify we don't latch onto them.
        val sb1Base = 0x02025734
        val ptrAddr = 0x03005008
        val bus = FakeBus()
        val sb1Off = sb1Base - RomCalibrator.EWRAM_BASE
        writeU16Le(bus.ewram, sb1Off + 0, 10)
        writeU32Le(bus.iwram, ptrAddr - RomCalibrator.IWRAM_BASE, sb1Base)
        val before = bus.readBytes(RomCalibrator.EWRAM_BASE, RomCalibrator.EWRAM_SIZE)!!
        // Jump from 10 → 25 (warp / fly). Not a step.
        writeU16Le(bus.ewram, sb1Off + 0, 25)

        val result = RomCalibrator.calibrate(bus, before)
        // No ±1 halfword changed → NoChangedHalfword.
        assertEquals(RomCalibrator.Result.NoChangedHalfword, result)
    }

    @Test
    fun findChangedHalfwords_returns_only_plus_minus_one_deltas() {
        val before = ByteArray(8)
        val after = ByteArray(8)
        // halfword 0: 100 → 99   (delta -1, included)
        writeU16Le(before, 0, 100); writeU16Le(after, 0, 99)
        // halfword 1: 200 → 200  (no change)
        writeU16Le(before, 2, 200); writeU16Le(after, 2, 200)
        // halfword 2: 5 → 7      (delta +2, excluded)
        writeU16Le(before, 4, 5); writeU16Le(after, 4, 7)
        // halfword 3: 50 → 51    (delta +1, included)
        writeU16Le(before, 6, 50); writeU16Le(after, 6, 51)

        val changed = RomCalibrator.findChangedHalfwords(before, after, baseAddr = 0x1000)
        assertEquals(listOf(0x1000, 0x1006), changed)
    }
}
