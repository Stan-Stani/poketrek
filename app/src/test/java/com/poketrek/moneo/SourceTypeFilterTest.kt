package com.poketrek.moneo

import com.poketrek.moneo.data.Area
import com.poketrek.moneo.data.MoneoCardStore
import com.poketrek.moneo.data.MoneoRepository
import com.poketrek.moneo.data.SeedLoader
import com.poketrek.moneo.data.VocabEntry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

/**
 * Covers the Off/Merged/Separate semantics added for the Pokémon moves and
 * abilities decks: a per-`primarySourceType` exclude list, a per-type
 * separate-into-pseudo-area list, and the pseudo-area id split parser.
 */
class SourceTypeFilterTest {

    @get:Rule val tempFolder = TemporaryFolder()

    private val areas = listOf(
        Area("pallet_town", "Pallet", "하나", 1),
        Area("route_1", "Route 1", "둘", 2),
    )

    // A Route 1 mix: 2 dialog vocab, 2 moves, 1 ability.
    private val sampleVocab = listOf(
        VocabEntry(
            id = "rom-mine-v3:야생", korean = "야생", gloss = "wild", partOfSpeech = "noun",
            areaId = "route_1", sourceTag = "rom-mine-v3",
            primarySourceType = "npc_dialog",
        ),
        VocabEntry(
            id = "rom-mine-v3:풀", korean = "풀", gloss = "grass", partOfSpeech = "noun",
            areaId = "route_1", sourceTag = "rom-mine-v3",
            primarySourceType = "npc_dialog",
        ),
        VocabEntry(
            id = "rom-mine-v3:막치기", korean = "막치기", gloss = "Pound", partOfSpeech = "noun",
            areaId = "rom_mined", sourceTag = "rom-mine-v3",
            areasReferenced = listOf("route_1", "viridian_city"),
            primarySourceType = "pokemon_move",
        ),
        VocabEntry(
            id = "rom-mine-v3:몸통박치기", korean = "몸통박치기", gloss = "Tackle", partOfSpeech = "noun",
            areaId = "rom_mined", sourceTag = "rom-mine-v3",
            areasReferenced = listOf("route_1"),
            primarySourceType = "pokemon_move",
        ),
        VocabEntry(
            id = "rom-mine-v3:면역", korean = "면역", gloss = "Immunity", partOfSpeech = "noun",
            areaId = "rom_mined", sourceTag = "rom-mine-v3",
            areasReferenced = listOf("route_1"),
            primarySourceType = "pokemon_ability",
        ),
    )

    private fun mkRepo() = MoneoRepository(
        store = MoneoCardStore(tempFolder.newFolder()),
        initialVocab = sampleVocab,
        initialAreas = areas,
        now = { 1_700_000_000_000L },
    )

    // ----- MERGED (default with both modes "MERGED") -----

    @Test fun mergedDefaultShowsEverythingInBaseArea() {
        val repo = mkRepo()
        assertEquals(5, repo.vocabForArea("route_1").size)
        // Pseudo-area lookups still resolve to the matching cards even when
        // separation is off — that's by design; visibility is gated by the
        // MoneoModule.buildAreaList advertising layer, not by vocabForArea.
        // (Separately verified in MoneoModule, not here.)
    }

    // ----- OFF -----

    @Test fun offHidesTypeFromAllAreas() {
        val repo = mkRepo()
        repo.setExcludedSourceTypes(setOf("pokemon_move"))
        val r1 = repo.vocabForArea("route_1")
        assertEquals(3, r1.size)
        assertTrue(r1.none { it.primarySourceType == "pokemon_move" })
        // And the pseudo-area is empty regardless (excluded > separated).
        assertEquals(0, repo.vocabForArea("route_1#pokemon_move").size)
    }

    @Test fun offHidesTypeFromTotalDueCount() {
        val repo = mkRepo()
        // Without any opt-out: all 5 cards are NEW → all due.
        assertEquals(5, repo.totalDueCount())
        repo.setExcludedSourceTypes(setOf("pokemon_move"))
        // Moves vanish from the global due count too.
        assertEquals(3, repo.totalDueCount())
    }

    // ----- SEPARATE -----

    @Test fun separateMovesIntoPseudoArea() {
        val repo = mkRepo()
        repo.setSeparatedSourceTypes(setOf("pokemon_move"))

        val baseR1 = repo.vocabForArea("route_1")
        // 2 dialog + 1 ability remain in base — moves were split out.
        assertEquals(3, baseR1.size)
        assertTrue(baseR1.none { it.primarySourceType == "pokemon_move" })

        val movesR1 = repo.vocabForArea("route_1#pokemon_move")
        assertEquals(2, movesR1.size)
        assertTrue(movesR1.all { it.primarySourceType == "pokemon_move" })
    }

    @Test fun separateBothTypesSplitsIndependently() {
        val repo = mkRepo()
        repo.setSeparatedSourceTypes(setOf("pokemon_move", "pokemon_ability"))

        assertEquals(2, repo.vocabForArea("route_1").size) // only dialog
        assertEquals(2, repo.vocabForArea("route_1#pokemon_move").size)
        assertEquals(1, repo.vocabForArea("route_1#pokemon_ability").size)
    }

    @Test fun separatedPseudoAreaRespectsAreasReferenced() {
        val repo = mkRepo()
        repo.setSeparatedSourceTypes(setOf("pokemon_move"))
        // 막치기 is referenced in route_1 AND viridian_city → should appear
        // in both pseudo-areas via the same areasReferenced lookup path.
        assertEquals(1, repo.vocabForArea("viridian_city#pokemon_move").size)
        assertEquals(2, repo.vocabForArea("route_1#pokemon_move").size)
    }

    // ----- OFF + SEPARATE interaction -----

    @Test fun excludedWinsOverSeparated() {
        val repo = mkRepo()
        repo.setExcludedSourceTypes(setOf("pokemon_move"))
        repo.setSeparatedSourceTypes(setOf("pokemon_move"))
        // Both filters claim the type; exclusion wins, pseudo-area is empty.
        assertEquals(0, repo.vocabForArea("route_1#pokemon_move").size)
        // Base area also reflects exclusion (not separation).
        assertEquals(3, repo.vocabForArea("route_1").size)
    }

    // ----- splitPseudoAreaId helper -----

    @Test fun splitPseudoAreaIdRoundTrips() {
        val repo = mkRepo()
        assertNull(repo.splitPseudoAreaId("route_1"))
        assertEquals("route_1" to "pokemon_move", repo.splitPseudoAreaId("route_1#pokemon_move"))
        assertEquals("rom_mined" to "pokemon_ability", repo.splitPseudoAreaId("rom_mined#pokemon_ability"))
    }

    // ----- SeedLoader parses primarySourceType -----

    @Test fun seedLoaderParsesPrimarySourceType() {
        val json = """
        {
          "version": 1,
          "sourceTag": "rom-mine-v3",
          "entries": [
            {
              "korean": "막치기", "gloss": "Pound", "partOfSpeech": "noun",
              "areaId": "rom_mined",
              "primarySourceType": "pokemon_move"
            },
            {
              "korean": "들다", "gloss": "to lift", "partOfSpeech": "verb",
              "areaId": "rom_mined"
            }
          ]
        }
        """.trimIndent()
        val parsed = SeedLoader.parse(json).associateBy { it.korean }
        assertNotNull(parsed["막치기"])
        assertEquals("pokemon_move", parsed["막치기"]!!.primarySourceType)
        // Missing field stays null (not "")
        assertNull(parsed["들다"]!!.primarySourceType)
    }
}
