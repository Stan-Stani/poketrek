package com.poketrek.moneo

import com.poketrek.moneo.data.MapBoundaryLookup
import com.poketrek.moneo.data.Boundary
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class MapBoundaryLookupTest {

    private val edgeOnlySample = """
        {
          "version": 1,
          "boundaries": {
            "1:0": [
              {"x":5,"y":0,"dir":"up","destBank":1,"destMapId":19,"destArea":"route_1","kind":"edge"}
            ]
          }
        }
    """.trimIndent()

    private val warpOnlySample = """
        {
          "version": 1,
          "boundaries": {
            "1:0": [
              {"x":12,"y":8,"dir":null,"destBank":2,"destMapId":0,"destArea":"viridian_forest","kind":"warp"}
            ]
          }
        }
    """.trimIndent()

    private val mixedSample = """
        {
          "version": 1,
          "boundaries": {
            "1:0": [
              {"x":5,"y":0,"dir":"up","destBank":1,"destMapId":19,"destArea":"route_1","kind":"edge"},
              {"x":12,"y":8,"dir":null,"destBank":2,"destMapId":0,"destArea":"viridian_forest","kind":"warp"},
              {"x":20,"y":3,"dir":"left","destBank":1,"destMapId":20,"destArea":"route_22","kind":"edge"}
            ]
          }
        }
    """.trimIndent()

    private val malformedSample = """
        {
          "version": 1,
          "boundaries": {
            "1:0": [
              {"x":5,"y":0,"dir":"up","destBank":1,"destMapId":19,"destArea":"route_1","kind":"edge"},
              {"x":5,"y":1,"dir":"down","destBank":1,"destMapId":19,"kind":"edge"},
              {"x":5,"y":0,"destArea":"bad_location"}
            ]
          }
        }
    """.trimIndent()

    @Test
    fun resolvesEdgeBoundary() {
        val lookup = MapBoundaryLookup.parse(edgeOnlySample)
        val boundary = lookup.boundaryAt(1, 0, 5, 0, "up")
        assertEquals("route_1", boundary?.destArea)
        assertNull(lookup.boundaryAt(1, 0, 5, 0, "down"))
        assertNull(lookup.boundaryAt(1, 0, 5, 0, "left"))
        assertNull(lookup.boundaryAt(1, 0, 5, 0, "right"))
        assertNull(lookup.boundaryAt(1, 0, 5, 0, null))
        assertNull(lookup.boundaryAt(1, 0, 4, 0, "up"))
    }

    @Test
    fun resolvesWarpRegardlessOfPressDir() {
        val lookup = MapBoundaryLookup.parse(warpOnlySample)
        val directions = arrayOf("left", "right", "up", "down", null)
        for (dir in directions) {
            val boundary = lookup.boundaryAt(1, 0, 12, 8, dir)
            assertEquals("viridian_forest", boundary?.destArea)
        }
    }

    @Test
    fun boundariesForReturnsAll() {
        val lookup = MapBoundaryLookup.parse(mixedSample)
        val all = lookup.boundariesFor(1, 0)
        assertEquals(3, all.size)
        val areas = all.map { it.destArea }.toSet()
        assertTrue(areas.contains("route_1"))
        assertTrue(areas.contains("viridian_forest"))
        assertTrue(areas.contains("route_22"))
    }

    @Test
    fun ignoresMalformedEntries() {
        val lookup = MapBoundaryLookup.parse(malformedSample)
        // The entry missing destArea should be ignored; the valid edge at (5,0,up) still works
        val boundary = lookup.boundaryAt(1, 0, 5, 0, "up")
        assertEquals("route_1", boundary?.destArea)
        // The entry with missing destArea (x=5,y=1,dir=down, no destArea) should be ignored,
        // so no boundary for that tile.
        assertNull(lookup.boundaryAt(1, 0, 5, 1, "down"))
        // The third entry is completely invalid, should also be ignored.
        // boundariesFor should still return only the valid ones (1)
        val all = lookup.boundariesFor(1, 0)
        assertEquals(1, all.size)
    }

    @Test
    fun emptyForUnknownMap() {
        val lookup = MapBoundaryLookup.parse(edgeOnlySample)
        assertTrue(lookup.boundariesFor(99, 99).isEmpty())
        assertNull(lookup.boundaryAt(99, 99, 0, 0, "up"))
    }
}