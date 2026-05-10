package com.poketrek.moneo

import com.poketrek.moneo.data.Area
import com.poketrek.moneo.data.MoneoCardStore
import com.poketrek.moneo.data.MoneoRepository
import com.poketrek.moneo.data.SeedLoader
import com.poketrek.moneo.data.VocabEntry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

/**
 * Coverage for [MoneoRepository.vocabForArea] matching cards by either
 * [VocabEntry.areaId] or [VocabEntry.areasReferenced]. Regression guard for
 * the route_1 attribution gap: words first encountered in Pallet that ALSO
 * surface in Route 1 dialog should appear in Route 1's review queue.
 */
class VocabForAreaTest {

    @get:Rule val tempFolder = TemporaryFolder()

    private val areas = listOf(
        Area("pallet_town", "Pallet", "하나", 1),
        Area("route_1", "Route 1", "둘", 2),
        Area("viridian_city", "Viridian", "셋", 3),
    )

    private fun mkRepo(initialVocab: List<VocabEntry>) = MoneoRepository(
        store = MoneoCardStore(tempFolder.newFolder()),
        initialVocab = initialVocab,
        initialAreas = areas,
        now = { 1_700_000_000_000L },
    )

    @Test fun homeAreaMatchStillWorks() {
        val repo = mkRepo(listOf(
            VocabEntry("t:가", "가", "go", "verb", areaId = "route_1", sourceTag = "t"),
        ))
        assertEquals(1, repo.vocabForArea("route_1").size)
        assertEquals(0, repo.vocabForArea("pallet_town").size)
    }

    @Test fun areasReferencedSurfacesCard() {
        val repo = mkRepo(listOf(
            VocabEntry(
                id = "t:받다", korean = "받다", gloss = "to receive", partOfSpeech = "verb",
                areaId = "pallet_town", sourceTag = "t",
                areasReferenced = listOf("pallet_town", "route_1", "viridian_city"),
            ),
        ))
        // Visible in pallet (home) AND in route_1 (referenced) AND viridian_city
        assertEquals(1, repo.vocabForArea("pallet_town").size)
        assertEquals(1, repo.vocabForArea("route_1").size)
        assertEquals(1, repo.vocabForArea("viridian_city").size)
    }

    @Test fun emptyAreasReferencedBehavesLikeBefore() {
        // Curated decks ship without areasReferenced — query must still respect
        // the legacy areaId-only semantics.
        val repo = mkRepo(listOf(
            VocabEntry("t:풀", "풀", "grass", "noun", areaId = "route_1", sourceTag = "t"),
        ))
        assertEquals(1, repo.vocabForArea("route_1").size)
        assertEquals(0, repo.vocabForArea("pallet_town").size)
    }

    @Test fun excludedSourceTagsStillFilter() {
        val repo = mkRepo(listOf(
            VocabEntry(
                "spec:꼬렛", "꼬렛", "Rattata", "noun",
                areaId = "rom_mined", sourceTag = "species-rom-2024",
                areasReferenced = listOf("route_1", "viridian_forest"),
            ),
        ))
        // Visible by default
        assertEquals(1, repo.vocabForArea("route_1").size)
        repo.setExcludedSourceTags(setOf("species-rom-2024"))
        // Hidden after the user opts out of species cards
        assertEquals(0, repo.vocabForArea("route_1").size)
    }

    @Test fun seedLoaderParsesAreasReferenced() {
        val json = """
        {
          "version": 1,
          "sourceTag": "test",
          "entries": [
            {
              "korean": "들다", "gloss": "to lift", "partOfSpeech": "verb",
              "areaId": "rom_mined",
              "firstAreaEncountered": "pallet_town",
              "areasReferenced": ["pallet_town", "route_1", "route_2"]
            },
            {
              "korean": "풀", "gloss": "grass", "partOfSpeech": "noun",
              "areaId": "route_1"
            }
          ]
        }
        """.trimIndent()
        val parsed = SeedLoader.parse(json).associateBy { it.korean }
        // firstAreaEncountered wins for areaId
        assertEquals("pallet_town", parsed["들다"]!!.areaId)
        assertEquals(listOf("pallet_town", "route_1", "route_2"), parsed["들다"]!!.areasReferenced)
        // Curated entry without areasReferenced -> empty list
        assertEquals("route_1", parsed["풀"]!!.areaId)
        assertTrue(parsed["풀"]!!.areasReferenced.isEmpty())
    }
}
