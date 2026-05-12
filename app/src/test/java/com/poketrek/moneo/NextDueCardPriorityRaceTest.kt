package com.poketrek.moneo

import com.poketrek.moneo.data.Area
import com.poketrek.moneo.data.CardRecord
import com.poketrek.moneo.data.MoneoCardStore
import com.poketrek.moneo.data.MoneoRepository
import com.poketrek.moneo.data.VocabEntry
import com.poketrek.moneo.srs.CardSnapshot
import com.poketrek.moneo.srs.CardState
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

/**
 * Pins the priority-flip race that [com.poketrek.moneo.ui.ReviewScreen]
 * must defend against: at one moment `nextDueCard` returns a NEW card,
 * and a few seconds later (when a LEARNING card's `dueAt` elapses) the
 * same query returns the LEARNING card instead. The UI used to re-derive
 * on every recomposition; tapping "Reveal" on the NEW card therefore
 * surfaced a different card's definition. The fix pins the chosen card
 * to the `cards` state map so it only re-derives on grade/suspend.
 */
class NextDueCardPriorityRaceTest {

    @get:Rule
    val tempFolder = TemporaryFolder()

    @Test fun learningCardPreemptsNewCardOnceDue() {
        val store = MoneoCardStore(tempFolder.newFolder())
        val areaA = Area("aid", "Area", "지역", 0)
        val newCard = VocabEntry(
            id = "new",
            korean = "새",
            gloss = "new",
            partOfSpeech = "n",
            areaId = "aid",
            sourceTag = "tag",
        )
        val learningCard = VocabEntry(
            id = "learn",
            korean = "학",
            gloss = "learn",
            partOfSpeech = "n",
            areaId = "aid",
            sourceTag = "tag",
        )
        val t0 = 1_700_000_000_000L
        var clock = t0
        val repo = MoneoRepository(
            store = store,
            initialVocab = listOf(newCard, learningCard),
            initialAreas = listOf(areaA),
            now = { clock },
        )
        // Seed the "learning" card in LEARNING state with dueAt = t0 + 60s,
        // mirroring the state SM2 produces after grading "Again" on a NEW.
        store.put(
            CardRecord(
                vocabId = "learn",
                snapshot = CardSnapshot(
                    state = CardState.LEARNING,
                    learningStep = 0,
                    dueAt = t0 + 60_000L,
                ),
                createdAt = t0,
            ),
        )
        // Rehydrate so the in-memory cards map reflects the seeded record.
        val repo2 = MoneoRepository(
            store = store,
            initialVocab = listOf(newCard, learningCard),
            initialAreas = listOf(areaA),
            now = { clock },
        )

        // At t0: LEARNING not yet due, so the NEW card is chosen.
        val firstPick = repo2.nextDueCard("aid")
        assertEquals("new", firstPick?.first?.vocabId)

        // 61 s later, with no grade in between, the LEARNING card outranks
        // the NEW card and `nextDueCard` returns a *different* vocab. The
        // UI must NOT re-ask in this state, or it would silently swap the
        // card under the user's "Reveal" tap.
        clock = t0 + 61_000L
        val secondPick = repo2.nextDueCard("aid")
        assertEquals("learn", secondPick?.first?.vocabId)
    }
}
