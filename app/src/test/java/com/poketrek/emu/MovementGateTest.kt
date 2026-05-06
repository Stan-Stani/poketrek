package com.poketrek.emu

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Unit tests for [MovementGate]. Use a hand-rolled fake budget so the test
 * runs on the plain JVM (no Android Context, no DataStore, no Robolectric).
 *
 * The decrement contract under test:
 *   decrement IFF (X or Y changed since last frame)
 *               AND (a direction was held last frame)
 *               AND (mapBank/mapId unchanged)
 *
 * The masking contract under test:
 *   mask DIR bits IFF (gate enabled) AND (budget == 0) AND (direction held this frame)
 */
class MovementGateTest {

    private class FakeBudget(initialTiles: Int = 0, initialEnabled: Boolean = false) : MovementGateBudget {
        private val _budget = MutableStateFlow(initialTiles)
        private val _enabled = MutableStateFlow(initialEnabled)
        override val budget: StateFlow<Int> = _budget.asStateFlow()
        override val gateEnabled: StateFlow<Boolean> = _enabled.asStateFlow()
        var consumeCalls = 0
            private set
        override fun setGateEnabled(value: Boolean) { _enabled.value = value }
        override fun consumeOneTile(): Boolean {
            consumeCalls++
            val v = _budget.value
            if (v <= 0) return false
            _budget.value = v - 1
            return true
        }
        fun add(tiles: Int) { _budget.value += tiles }
    }

    private fun snap(x: Int = 5, y: Int = 5, mapId: Int = 1, mapBank: Int = 0) =
        LeafGreenRam.Snapshot(
            playerX = x, playerY = y, mapId = mapId, mapBank = mapBank,
            movingStatus = 0, saveBlockPtr = 0x02000000,
        )

    // ---- decrement rule -----------------------------------------------------

    @Test fun `tile change with direction held decrements budget`() {
        val b = FakeBudget(initialTiles = 10)
        val gate = MovementGate(b)
        // Frame 1: hold UP, no movement yet — gate sees nothing previous, no decrement.
        gate.process(GbaKey.UP, snap(x = 5, y = 5))
        assertEquals(0, b.consumeCalls)
        // Frame 2: still holding UP, Y changed by 1 — should consume.
        gate.process(GbaKey.UP, snap(x = 5, y = 4))
        assertEquals(1, b.consumeCalls)
        assertEquals(9, b.budget.value)
    }

    @Test fun `tile change with no direction held does not decrement`() {
        // Cutscene / scripted movement: player slides without any key held.
        val b = FakeBudget(initialTiles = 10)
        val gate = MovementGate(b)
        gate.process(0, snap(x = 5, y = 5))
        gate.process(0, snap(x = 5, y = 4)) // moved but no direction
        assertEquals(0, b.consumeCalls)
        assertEquals(10, b.budget.value)
    }

    @Test fun `same position with direction held does not decrement`() {
        // Bumping a wall: direction held but X/Y don't change.
        val b = FakeBudget(initialTiles = 10)
        val gate = MovementGate(b)
        gate.process(GbaKey.RIGHT, snap(x = 5, y = 5))
        gate.process(GbaKey.RIGHT, snap(x = 5, y = 5)) // unchanged
        assertEquals(0, b.consumeCalls)
        assertEquals(10, b.budget.value)
    }

    @Test fun `map change does not decrement (warp through door)`() {
        val b = FakeBudget(initialTiles = 10)
        val gate = MovementGate(b)
        gate.process(GbaKey.DOWN, snap(x = 5, y = 5, mapId = 1))
        // New map: X reset to 7, but mapId changed → don't charge for the warp tile.
        gate.process(GbaKey.DOWN, snap(x = 7, y = 1, mapId = 2))
        assertEquals(0, b.consumeCalls)
        assertEquals(10, b.budget.value)
    }

    @Test fun `map bank change also does not decrement`() {
        val b = FakeBudget(initialTiles = 10)
        val gate = MovementGate(b)
        gate.process(GbaKey.DOWN, snap(x = 5, y = 5, mapBank = 0))
        gate.process(GbaKey.DOWN, snap(x = 5, y = 6, mapBank = 1)) // bank changed
        assertEquals(0, b.consumeCalls)
    }

    @Test fun `multiple sequential tile changes each decrement once`() {
        val b = FakeBudget(initialTiles = 10)
        val gate = MovementGate(b)
        gate.process(GbaKey.RIGHT, snap(x = 5, y = 5))
        gate.process(GbaKey.RIGHT, snap(x = 6, y = 5))
        gate.process(GbaKey.RIGHT, snap(x = 7, y = 5))
        gate.process(GbaKey.RIGHT, snap(x = 8, y = 5))
        // First call has no prev to diff against; remaining 3 decrement.
        assertEquals(3, b.consumeCalls)
        assertEquals(7, b.budget.value)
    }

    // ---- masking rule -------------------------------------------------------

    @Test fun `disabled gate never masks even when budget is zero`() {
        val b = FakeBudget(initialTiles = 0, initialEnabled = false)
        val gate = MovementGate(b)
        val out = gate.process(GbaKey.UP or GbaKey.A, snap())
        assertEquals(GbaKey.UP or GbaKey.A, out)
    }

    @Test fun `enabled gate with zero budget masks direction bits but preserves A B`() {
        val b = FakeBudget(initialTiles = 0, initialEnabled = true)
        val gate = MovementGate(b)
        val raw = GbaKey.UP or GbaKey.A or GbaKey.B
        val out = gate.process(raw, snap())
        assertEquals(0, out and GbaKey.UP)
        assertEquals(GbaKey.A, out and GbaKey.A)
        assertEquals(GbaKey.B, out and GbaKey.B)
    }

    @Test fun `enabled gate with positive budget does not mask`() {
        val b = FakeBudget(initialTiles = 5, initialEnabled = true)
        val gate = MovementGate(b)
        val out = gate.process(GbaKey.DOWN, snap())
        assertEquals(GbaKey.DOWN, out)
    }

    @Test fun `enabled gate masks all four directions when budget exhausted`() {
        val b = FakeBudget(initialTiles = 0, initialEnabled = true)
        val gate = MovementGate(b)
        val raw = GbaKey.UP or GbaKey.DOWN or GbaKey.LEFT or GbaKey.RIGHT or GbaKey.START
        val out = gate.process(raw, snap())
        assertEquals(0, out and GbaKey.UP)
        assertEquals(0, out and GbaKey.DOWN)
        assertEquals(0, out and GbaKey.LEFT)
        assertEquals(0, out and GbaKey.RIGHT)
        assertEquals(GbaKey.START, out and GbaKey.START)
    }

    // ---- prevKeys uses MASKED bits, not raw --------------------------------

    @Test fun `decrement diff uses masked keys so blocked direction does not credit later movement`() {
        // Subtle: if we exhaust the budget while UP is held, mask UP, then
        // refill the budget — the *next* frame must not retroactively count
        // a tile transition just because raw-UP was held last frame.
        // Concretely: prevKeys must reflect the masked bits, so an exhausted
        // hold doesn't satisfy the "direction held last frame" condition.
        val b = FakeBudget(initialTiles = 0, initialEnabled = true)
        val gate = MovementGate(b)
        // Frame 1: hold UP, budget=0 → masked to 0. No prev, no decrement.
        gate.process(GbaKey.UP, snap(x = 5, y = 5))
        // Frame 2: refill budget to 10. Game engine independently moves Y by 1
        // (e.g. scripted) while UP is still held raw but masked. Should NOT
        // decrement, because last frame's direction (after masking) was 0.
        b.add(10)
        gate.process(GbaKey.UP, snap(x = 5, y = 4))
        assertEquals(0, b.consumeCalls)
    }

    // ---- setEnabled -------------------------------------------------------

    @Test fun `setEnabled flips the budget enabled flag`() {
        val b = FakeBudget(initialEnabled = false)
        val gate = MovementGate(b)
        assertFalse(gate.enabled.value)
        gate.setEnabled(true)
        assertTrue(gate.enabled.value)
        assertTrue(b.gateEnabled.value)
        // Sanity: not the same instance? — they should literally be the same flow.
        assertEquals(b.gateEnabled, gate.enabled)
        // Toggling via budget directly is also visible to the gate.
        b.setGateEnabled(false)
        assertFalse(gate.enabled.value)
    }

    @Test fun `mask is independent of decrement on the same frame`() {
        // Frame where (a) we'd decrement (dir+movement+same map) AND
        // (b) gate is enabled and budget will hit zero. The current
        // implementation reads budget.value for masking AFTER consume
        // already ran — but only if enabled+zero+dir. Verify the order
        // doesn't accidentally double-charge or drop a tile.
        val b = FakeBudget(initialTiles = 1, initialEnabled = true)
        val gate = MovementGate(b)
        gate.process(GbaKey.UP, snap(x = 5, y = 5))            // priming
        val out = gate.process(GbaKey.UP, snap(x = 5, y = 4))  // moved → consume → 0
        assertEquals(1, b.consumeCalls)
        assertEquals(0, b.budget.value)
        // Budget hit zero this same frame → mask kicks in for THIS frame's keys.
        assertEquals(0, out and GbaKey.UP)
        // Make sure other bits would have passed through.
        assertNotEquals(GbaKey.A, out and GbaKey.A) // A wasn't held; nothing to assert vs mask
    }
}
