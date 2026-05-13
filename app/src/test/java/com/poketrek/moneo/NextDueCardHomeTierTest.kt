package com.poketrek.moneo

import com.poketrek.moneo.data.Area
import com.poketrek.moneo.data.CardRecord
import com.poketrek.moneo.data.MoneoCardStore
import com.poketrek.moneo.data.MoneoRepository
import com.poketrek.moneo.data.VocabEntry
import com.poketrek.moneo.srs.CardSnapshot
import com.poketrek.moneo.srs.CardState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

/**
 * Two-tier queue: cards whose [VocabEntry.areaId] matches the queried area
 * (the "home" tier) must be exhausted before cards visible only via
 * [VocabEntry.areasReferenced] (the "referenced" tier) surface. This is the
 * fix for Pallet Town drowning in 400+ broadly-referenced ROM-mined cards.
 */
class NextDueCardHomeTierTest {

    @get:Rule val tempFolder = TemporaryFolder()

    private val areas = listOf(
        Area("pallet_town", "Pallet", "태초", 1),
        Area("route_1", "Route 1", "1번 도로", 2),
    )

    private fun mkRepo(initialVocab: List<VocabEntry>) = MoneoRepository(
        store = MoneoCardStore(tempFolder.newFolder()),
        initialVocab = initialVocab,
        initialAreas = areas,
        now = { 1_700_000_000_000L },
    )

    @Test fun homeCardPrecedesReferencedCard() {
        val homeCard = VocabEntry(
            id = "home:집", korean = "집", gloss = "house", partOfSpeech = "noun",
            areaId = "pallet_town", sourceTag = "t",
        )
        val refOnlyCard = VocabEntry(
            id = "ref:링", korean = "링", gloss = "ring", partOfSpeech = "noun",
            areaId = "rom_mined", sourceTag = "t",
            areasReferenced = listOf("pallet_town", "route_1"),
        )
        val repo = mkRepo(listOf(homeCard, refOnlyCard))

        // Both are visible in Pallet Town's queue …
        assertEquals(2, repo.vocabForArea("pallet_town").size)
        // … but the home card is picked first.
        val first = repo.nextDueCard("pallet_town")
        assertEquals("home:집", first?.first?.vocabId)
    }

    @Test fun referencedCardAppearsOnlyAfterHomeIsExhausted() {
        val homeCard = VocabEntry(
            id = "home:집", korean = "집", gloss = "house", partOfSpeech = "noun",
            areaId = "pallet_town", sourceTag = "t",
        )
        val refOnlyCard = VocabEntry(
            id = "ref:링", korean = "링", gloss = "ring", partOfSpeech = "noun",
            areaId = "rom_mined", sourceTag = "t",
            areasReferenced = listOf("pallet_town"),
        )
        val t0 = 1_700_000_000_000L
        val store = MoneoCardStore(tempFolder.newFolder())
        // Park the home card in LEARNING with dueAt far in the future, so the
        // home tier has no card due *right now*.
        store.put(
            CardRecord(
                vocabId = "home:집",
                snapshot = CardSnapshot(
                    state = CardState.LEARNING,
                    learningStep = 0,
                    dueAt = t0 + 24 * 60 * 60_000L,
                ),
                createdAt = t0,
            ),
        )
        val repo = MoneoRepository(
            store = store,
            initialVocab = listOf(homeCard, refOnlyCard),
            initialAreas = areas,
            now = { t0 },
        )

        // Home tier has no due card -> fall through to referenced tier.
        val pick = repo.nextDueCard("pallet_town")
        assertEquals("ref:링", pick?.first?.vocabId)
    }

    @Test fun homeCardPreemptsReferencedOnceItBecomesDue() {
        val homeCard = VocabEntry(
            id = "home:집", korean = "집", gloss = "house", partOfSpeech = "noun",
            areaId = "pallet_town", sourceTag = "t",
        )
        val refOnlyCard = VocabEntry(
            id = "ref:링", korean = "링", gloss = "ring", partOfSpeech = "noun",
            areaId = "rom_mined", sourceTag = "t",
            areasReferenced = listOf("pallet_town"),
        )
        val t0 = 1_700_000_000_000L
        var clock = t0
        val store = MoneoCardStore(tempFolder.newFolder())
        // Home card seeded LEARNING with dueAt = t0 + 60s (mirrors post-"Again" state).
        store.put(
            CardRecord(
                vocabId = "home:집",
                snapshot = CardSnapshot(
                    state = CardState.LEARNING,
                    learningStep = 0,
                    dueAt = t0 + 60_000L,
                ),
                createdAt = t0,
            ),
        )
        val repo = MoneoRepository(
            store = store,
            initialVocab = listOf(homeCard, refOnlyCard),
            initialAreas = areas,
            now = { clock },
        )

        // At t0 the home LEARNING isn't due yet, so we drop to the referenced tier.
        assertEquals("ref:링", repo.nextDueCard("pallet_town")?.first?.vocabId)

        // 61s later the home card is due — it must preempt the referenced card.
        clock = t0 + 61_000L
        assertEquals("home:집", repo.nextDueCard("pallet_town")?.first?.vocabId)
    }

    @Test fun pseudoAreaSplitRespectsHomeTier() {
        // pallet_town#pokemon_move pseudo-area: only cards with
        // primarySourceType = pokemon_move. Within that filter the home/ref
        // split still applies based on the *base* areaId.
        val homeMove = VocabEntry(
            id = "home:박치기", korean = "박치기", gloss = "Headbutt", partOfSpeech = "noun",
            areaId = "pallet_town", sourceTag = "t",
            primarySourceType = "pokemon_move",
        )
        val refMove = VocabEntry(
            id = "ref:할퀴기", korean = "할퀴기", gloss = "Scratch", partOfSpeech = "noun",
            areaId = "rom_mined", sourceTag = "t",
            areasReferenced = listOf("pallet_town"),
            primarySourceType = "pokemon_move",
        )
        // A non-move card with home in pallet — must NOT leak into the pseudo-area.
        val homeNoun = VocabEntry(
            id = "home:집", korean = "집", gloss = "house", partOfSpeech = "noun",
            areaId = "pallet_town", sourceTag = "t",
        )
        val repo = mkRepo(listOf(homeMove, refMove, homeNoun))
        repo.setSeparatedSourceTypes(setOf("pokemon_move"))

        val pick = repo.nextDueCard("pallet_town#pokemon_move")
        assertEquals("home:박치기", pick?.first?.vocabId)
    }

    @Test fun referencedOnlyAreaSeesReferencedTier() {
        // Route 1 has no home cards in this fixture — every visible card is
        // referenced. The home tier is empty so the referenced tier is the
        // only source, which must still pick correctly.
        val refCard = VocabEntry(
            id = "ref:링", korean = "링", gloss = "ring", partOfSpeech = "noun",
            areaId = "rom_mined", sourceTag = "t",
            areasReferenced = listOf("route_1"),
        )
        val repo = mkRepo(listOf(refCard))
        val pick = repo.nextDueCard("route_1")
        assertNotNull(pick)
        assertEquals("ref:링", pick?.first?.vocabId)
    }

    @Test fun emptyAreaReturnsNull() {
        val repo = mkRepo(emptyList())
        assertNull(repo.nextDueCard("pallet_town"))
    }
}
