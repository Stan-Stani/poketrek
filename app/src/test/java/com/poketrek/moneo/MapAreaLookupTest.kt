package com.poketrek.moneo

import com.poketrek.moneo.data.MapAreaLookup
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class MapAreaLookupTest {

    private val sample = """
        {
          "version": 1,
          "rom": "leafgreen-kr-2024",
          "maps": {
            "0:0": "pallet_town",
            "1:2": "pewter_city",
            "1:20": "route_2"
          }
        }
    """.trimIndent()

    @Test fun resolvesKnownPairs() {
        val lookup = MapAreaLookup.parse(sample)
        assertEquals("pallet_town", lookup.areaIdFor(0, 0))
        assertEquals("pewter_city", lookup.areaIdFor(1, 2))
        assertEquals("route_2", lookup.areaIdFor(1, 20))
    }

    @Test fun returnsNullForUnknownPair() {
        val lookup = MapAreaLookup.parse(sample)
        assertNull(lookup.areaIdFor(99, 99))
        assertNull(lookup.areaIdFor(0, 99))
    }

    @Test fun ignoresMalformedKeys() {
        val malformed = """
            { "version": 1, "maps": { "garbage": "x", "0:0": "pallet_town", "1:abc": "y" } }
        """.trimIndent()
        val lookup = MapAreaLookup.parse(malformed)
        assertEquals("pallet_town", lookup.areaIdFor(0, 0))
        assertNull(lookup.areaIdFor(1, 0))
    }
}
