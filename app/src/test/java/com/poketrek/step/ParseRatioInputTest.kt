package com.poketrek.step

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ParseRatioInputTest {
    @Test fun integerInput() {
        assertEquals(4 to 1, parseRatioInput("4"))
        assertEquals(1 to 1, parseRatioInput("1"))
    }

    @Test fun decimalReducesToFraction() {
        assertEquals(5 to 2, parseRatioInput("2.5"))
        assertEquals(1 to 4, parseRatioInput("0.25"))
        assertEquals(1 to 1, parseRatioInput("1.0"))
        assertEquals(7 to 5, parseRatioInput("1.4"))
    }

    @Test fun fractionInput() {
        assertEquals(5 to 2, parseRatioInput("5/2"))
        assertEquals(1 to 3, parseRatioInput("1/3"))
        // reduces
        assertEquals(2 to 1, parseRatioInput("8/4"))
    }

    @Test fun whitespaceTolerated() {
        assertEquals(5 to 2, parseRatioInput("  5 / 2 "))
        assertEquals(5 to 2, parseRatioInput(" 2.5 "))
    }

    @Test fun rejectsGarbage() {
        assertNull(parseRatioInput(""))
        assertNull(parseRatioInput("abc"))
        assertNull(parseRatioInput("1/0"))
        assertNull(parseRatioInput("0"))
        assertNull(parseRatioInput("-1"))
        assertNull(parseRatioInput("1/2/3"))
        assertNull(parseRatioInput("1.2.3"))
        assertNull(parseRatioInput("."))
        assertNull(parseRatioInput("/"))
    }

    @Test fun rejectsOutOfRange() {
        // MAX is 1000; 1001 must be rejected
        assertNull(parseRatioInput("1001"))
        assertNull(parseRatioInput("1/1001"))
        // an irreducible fraction whose denominator overflows after parse
        assertNull(parseRatioInput("0.0001"))  // 1/10000
    }

    @Test fun acceptsNearMax() {
        assertEquals(1000 to 1, parseRatioInput("1000"))
        assertEquals(1 to 1000, parseRatioInput("1/1000"))
    }
}
