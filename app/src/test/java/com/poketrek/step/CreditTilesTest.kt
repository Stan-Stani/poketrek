package com.poketrek.step

import org.junit.Assert.assertEquals
import org.junit.Test

class CreditTilesTest {

    @Test fun `1_to_1 realistic — one step grants one tile`() {
        val (tiles, carry) = creditTiles(deltaSteps = 1, num = 1, den = 1, carryIn = 0)
        assertEquals(1L, tiles)
        assertEquals(0, carry)
    }

    @Test fun `4_to_1 default — one step grants four tiles`() {
        val (tiles, carry) = creditTiles(1, num = 4, den = 1, carryIn = 0)
        assertEquals(4L, tiles)
        assertEquals(0, carry)
    }

    @Test fun `1_to_2 hard — single step grants zero with carry`() {
        val (tiles, carry) = creditTiles(1, num = 1, den = 2, carryIn = 0)
        assertEquals(0L, tiles)
        assertEquals(1, carry)
    }

    @Test fun `1_to_2 hard — two steps total grant one tile across two calls`() {
        val (tiles1, carry1) = creditTiles(1, num = 1, den = 2, carryIn = 0)
        assertEquals(0L, tiles1); assertEquals(1, carry1)
        val (tiles2, carry2) = creditTiles(1, num = 1, den = 2, carryIn = carry1)
        assertEquals(1L, tiles2); assertEquals(0, carry2)
    }

    @Test fun `1_to_2 — batched 7 steps yields 3 tiles with carry 1`() {
        val (tiles, carry) = creditTiles(7, num = 1, den = 2, carryIn = 0)
        assertEquals(3L, tiles)
        assertEquals(1, carry)
    }

    @Test fun `1_to_3 — three calls of one step grant one tile total`() {
        var carry = 0
        var total = 0L
        repeat(3) {
            val (t, c) = creditTiles(1, num = 1, den = 3, carryIn = carry)
            total += t
            carry = c
        }
        assertEquals(1L, total)
        assertEquals(0, carry)
    }

    @Test fun `8_to_1 — one step yields 8 tiles`() {
        val (tiles, carry) = creditTiles(1, num = 8, den = 1, carryIn = 0)
        assertEquals(8L, tiles)
        assertEquals(0, carry)
    }

    @Test fun `large batch with sub-1 ratio is exact`() {
        // 1000 steps at 1:8 should give exactly 125 tiles, carry 0.
        val (tiles, carry) = creditTiles(1000, num = 1, den = 8, carryIn = 0)
        assertEquals(125L, tiles)
        assertEquals(0, carry)
    }

    @Test fun `non-integer batch with sub-1 ratio carries leftover`() {
        // 1003 steps at 1:8 → 125 tiles, carry 3 (the remaining 3 steps).
        val (tiles, carry) = creditTiles(1003, num = 1, den = 8, carryIn = 0)
        assertEquals(125L, tiles)
        assertEquals(3, carry)
    }

    @Test fun `zero or negative delta grants nothing and preserves carry`() {
        val (tiles0, carry0) = creditTiles(0, num = 1, den = 2, carryIn = 1)
        assertEquals(0L, tiles0); assertEquals(1, carry0)
        val (tilesNeg, carryNeg) = creditTiles(-5, num = 1, den = 2, carryIn = 1)
        assertEquals(0L, tilesNeg); assertEquals(1, carryNeg)
    }

    @Test fun `huge delta does not overflow Int`() {
        // 2_000_000_000 steps at 16:1 would overflow a 32-bit accumulator.
        // Function uses Long internally so this should produce a clean Long.
        val (tiles, carry) = creditTiles(2_000_000_000L, num = 16, den = 1, carryIn = 0)
        assertEquals(32_000_000_000L, tiles)
        assertEquals(0, carry)
    }

    @Test fun `requires positive ratio parts`() {
        try {
            creditTiles(1, num = 0, den = 1, carryIn = 0)
            error("expected IllegalArgumentException")
        } catch (_: IllegalArgumentException) { /* expected */ }
        try {
            creditTiles(1, num = 1, den = 0, carryIn = 0)
            error("expected IllegalArgumentException")
        } catch (_: IllegalArgumentException) { /* expected */ }
    }
}
