package com.poketrek.moneo

import com.poketrek.moneo.data.Area
import com.poketrek.moneo.data.CardRecord
import com.poketrek.moneo.data.MoneoCardStore
import com.poketrek.moneo.data.MoneoRepository
import com.poketrek.moneo.data.VocabEntry
import com.poketrek.moneo.srs.CardSnapshot
import com.poketrek.moneo.srs.CardState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File

class SuspendedCardsTest {

    @get:Rule
    val tempFolder = TemporaryFolder()

    private val now = 1_700_000_000_000L
    private val areaA = Area(
        id = "aid",
        englishName = "Area A",
        koreanLabel = "지역",
        ordinal = 0,
    )

    private fun vocab(id: String, korean: String = "가"): VocabEntry = VocabEntry(
        id = id,
        korean = korean,
        romanization = "ga",
        gloss = "go",
        partOfSpeech = "verb",
        areaId = "aid",
        sourceTag = "tag",
    )

    private fun newRecord(id: String): CardRecord = CardRecord(
        vocabId = id,
        snapshot = CardSnapshot(state = CardState.NEW),
        createdAt = now,
    )

    private fun makeRepo(
        store: MoneoCardStore,
        vocab: List<VocabEntry>,
    ): MoneoRepository = MoneoRepository(
        store = store,
        initialVocab = vocab,
        initialAreas = listOf(areaA),
        now = { now },
    )

    @Test fun setSuspendedHidesCardFromNextDueCard() {
        val store = MoneoCardStore(tempFolder.newFolder())
        val v = vocab("v1")
        val repo = makeRepo(store, listOf(v))

        assertNotNull(repo.nextDueCard("aid"))

        repo.setSuspended("v1", true)
        assertNull(repo.nextDueCard("aid"))

        repo.setSuspended("v1", false)
        assertNotNull(repo.nextDueCard("aid"))
    }

    @Test fun setSuspendedExcludesCardFromDueCounts() {
        val store = MoneoCardStore(tempFolder.newFolder())
        val v1 = vocab("v1", korean = "가")
        val v2 = vocab("v2", korean = "나")
        val repo = makeRepo(store, listOf(v1, v2))

        assertEquals(2, repo.dueCountForArea("aid"))
        assertEquals(2, repo.totalDueCount())

        repo.setSuspended("v1", true)
        assertEquals(1, repo.dueCountForArea("aid"))
        assertEquals(1, repo.totalDueCount())

        repo.setSuspended("v1", false)
        assertEquals(2, repo.dueCountForArea("aid"))
        assertEquals(2, repo.totalDueCount())
    }

    @Test fun setSuspendedUnknownVocabIdDoesNotThrow() {
        val store = MoneoCardStore(tempFolder.newFolder())
        val repo = makeRepo(store, emptyList())
        repo.setSuspended("nonexistent", true)
        repo.setSuspended("nonexistent", false)
    }

    @Test fun suspendedFlagPersistsThroughStoreRoundTrip() {
        val dir = tempFolder.newFolder()
        val store1 = MoneoCardStore(dir)
        val card = newRecord("v").copy(suspended = true)
        store1.put(card)

        val store2 = MoneoCardStore(dir)
        val loaded = store2.get("v")
        assertNotNull(loaded)
        assertTrue(loaded!!.suspended)
    }

    @Test fun legacyCardsJsonLoadsWithSuspendedFalse() {
        val dir = tempFolder.newFolder()
        val cardsFile = File(dir, "cards.json")
        // Mirrors MoneoCardStore.serialize() but omits the "suspended" key, as
        // older builds wrote. Loader must default suspended=false.
        val json = """
            {
              "version": 1,
              "cards": [
                {
                  "id": "legacy",
                  "createdAt": $now,
                  "state": "NEW",
                  "dueAt": 0,
                  "intervalDays": 0.0,
                  "ease": 2.5,
                  "reps": 0,
                  "lapses": 0,
                  "learningStep": 0
                }
              ]
            }
        """.trimIndent()
        cardsFile.writeText(json)

        val store = MoneoCardStore(dir)
        val card = store.get("legacy")
        assertNotNull(card)
        assertFalse(card!!.suspended)
    }
}
