package com.poketrek.moneo

import com.poketrek.moneo.srs.CardSnapshot
import com.poketrek.moneo.srs.CardState
import com.poketrek.moneo.srs.Rating
import com.poketrek.moneo.srs.Sm2
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class Sm2Test {

    private val now: Long = 1_700_000_000_000L

    @Test fun newCardGoodEntersFirstAdvanceLearningStep() {
        val card = CardSnapshot()
        val out = Sm2.schedule(card, Rating.GOOD, now)
        // With two learning steps, NEW + GOOD lands on step 1 (10 minutes).
        assertEquals(CardState.LEARNING, out.state)
        assertEquals(1, out.learningStep)
        assertEquals(now + CardSnapshot.LEARNING_STEPS_MS[1], out.dueAt)
    }

    @Test fun newCardAgainGoesToFirstLearningStep() {
        val out = Sm2.schedule(CardSnapshot(), Rating.AGAIN, now)
        assertEquals(CardState.LEARNING, out.state)
        assertEquals(0, out.learningStep)
        assertEquals(now + CardSnapshot.LEARNING_STEPS_MS[0], out.dueAt)
    }

    @Test fun newCardEasyGraduatesStraightToReview() {
        val out = Sm2.schedule(CardSnapshot(), Rating.EASY, now)
        assertEquals(CardState.REVIEW, out.state)
        assertEquals(CardSnapshot.EASY_GRADUATING_INTERVAL_DAYS, out.intervalDays, 1e-6)
    }

    @Test fun learningStep1GoodGraduatesToReview() {
        val card = CardSnapshot(state = CardState.LEARNING, learningStep = 1)
        val out = Sm2.schedule(card, Rating.GOOD, now)
        assertEquals(CardState.REVIEW, out.state)
        assertEquals(CardSnapshot.GRADUATING_INTERVAL_DAYS, out.intervalDays, 1e-6)
        assertEquals(now + CardSnapshot.DAY_MS, out.dueAt)
    }

    @Test fun reviewGoodMultipliesIntervalByEase() {
        val card = CardSnapshot(
            state = CardState.REVIEW,
            intervalDays = 4.0,
            ease = 2.5,
            reps = 2,
        )
        val out = Sm2.schedule(card, Rating.GOOD, now)
        assertEquals(10.0, out.intervalDays, 1e-6)
        assertEquals(2.5, out.ease, 1e-6)
        assertEquals(3, out.reps)
    }

    @Test fun reviewAgainLapsesAndDropsEase() {
        val card = CardSnapshot(
            state = CardState.REVIEW,
            intervalDays = 12.0,
            ease = 2.5,
            reps = 3,
        )
        val out = Sm2.schedule(card, Rating.AGAIN, now)
        assertEquals(CardState.LEARNING, out.state)
        assertEquals(0, out.learningStep)
        assertEquals(2.3, out.ease, 1e-6)
        assertEquals(1, out.lapses)
        assertEquals(0.0, out.intervalDays, 1e-6)
    }

    @Test fun reviewHardClampsEaseToFloor() {
        val card = CardSnapshot(
            state = CardState.REVIEW,
            intervalDays = 5.0,
            ease = CardSnapshot.MIN_EASE + 0.05,
        )
        val out = Sm2.schedule(card, Rating.HARD, now)
        assertEquals(CardSnapshot.MIN_EASE, out.ease, 1e-6)
    }

    @Test fun reviewEasyBumpsEaseAndUsesEasyMultiplier() {
        val card = CardSnapshot(
            state = CardState.REVIEW,
            intervalDays = 4.0,
            ease = 2.5,
        )
        val out = Sm2.schedule(card, Rating.EASY, now)
        assertEquals(2.65, out.ease, 1e-6)
        // 4.0 * 2.5 * 1.3 = 13.0
        assertEquals(13.0, out.intervalDays, 1e-6)
    }

    @Test fun reviewHardEnforcesIntervalIncrease() {
        // 1.2 * 0.5d = 0.6d — but we floor at intervalDays + 1.0 to ensure
        // the card actually moves forward.
        val card = CardSnapshot(
            state = CardState.REVIEW,
            intervalDays = 0.5,
            ease = 2.0,
        )
        val out = Sm2.schedule(card, Rating.HARD, now)
        assertTrue("interval should grow, was ${out.intervalDays}", out.intervalDays >= 1.5)
    }
}
