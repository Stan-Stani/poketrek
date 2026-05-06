package com.poketrek.moneo.srs

/**
 * Pure SM-2-flavored spaced-repetition scheduler. Anki-style adjustments:
 * ease floor 1.3, two learning steps (1m / 10m), graduating interval 1 day.
 * No Android dependency — unit-tested on the JVM.
 */

enum class CardState { NEW, LEARNING, REVIEW }

enum class Rating { AGAIN, HARD, GOOD, EASY }

data class CardSnapshot(
    val state: CardState = CardState.NEW,
    /** Epoch millis when the card next becomes due. */
    val dueAt: Long = 0L,
    /** Days between this review and the next, when in REVIEW state. */
    val intervalDays: Double = 0.0,
    /** SM-2 ease factor. Starts at 2.5; floored at 1.3. */
    val ease: Double = STARTING_EASE,
    /** Number of successful reviews in the REVIEW state. */
    val reps: Int = 0,
    /** How many times this card has lapsed back to LEARNING. */
    val lapses: Int = 0,
    /** Index into [LEARNING_STEPS_MS] when state == LEARNING. */
    val learningStep: Int = 0,
) {
    companion object {
        const val STARTING_EASE: Double = 2.5
        const val MIN_EASE: Double = 1.3
        const val GRADUATING_INTERVAL_DAYS: Double = 1.0
        const val EASY_GRADUATING_INTERVAL_DAYS: Double = 4.0

        /** Learning steps in milliseconds. Mirrors Anki defaults (1m, 10m). */
        val LEARNING_STEPS_MS: LongArray = longArrayOf(60_000L, 600_000L)

        const val DAY_MS: Long = 24L * 60L * 60L * 1000L
    }
}

object Sm2 {

    /**
     * Schedule [card] given a [rating] applied at [now] (epoch millis).
     * Returns the new card snapshot. Pure: same inputs → same output.
     */
    fun schedule(card: CardSnapshot, rating: Rating, now: Long): CardSnapshot {
        return when (card.state) {
            CardState.NEW -> scheduleFromNew(card, rating, now)
            CardState.LEARNING -> scheduleFromLearning(card, rating, now)
            CardState.REVIEW -> scheduleFromReview(card, rating, now)
        }
    }

    private fun scheduleFromNew(card: CardSnapshot, rating: Rating, now: Long): CardSnapshot {
        // Treat NEW like a LEARNING card at step 0; AGAIN/HARD set learning steps;
        // GOOD advances normally; EASY graduates straight to REVIEW.
        return when (rating) {
            Rating.AGAIN -> card.copy(
                state = CardState.LEARNING,
                learningStep = 0,
                dueAt = now + CardSnapshot.LEARNING_STEPS_MS[0],
            )
            Rating.HARD -> card.copy(
                state = CardState.LEARNING,
                learningStep = 0,
                dueAt = now + CardSnapshot.LEARNING_STEPS_MS[0],
            )
            Rating.GOOD -> {
                // Move to next learning step; if no more steps, graduate.
                val nextStep = 1
                if (nextStep >= CardSnapshot.LEARNING_STEPS_MS.size) {
                    graduateToReview(card, CardSnapshot.GRADUATING_INTERVAL_DAYS, now)
                } else {
                    card.copy(
                        state = CardState.LEARNING,
                        learningStep = nextStep,
                        dueAt = now + CardSnapshot.LEARNING_STEPS_MS[nextStep],
                    )
                }
            }
            Rating.EASY -> graduateToReview(
                card,
                CardSnapshot.EASY_GRADUATING_INTERVAL_DAYS,
                now,
            )
        }
    }

    private fun scheduleFromLearning(card: CardSnapshot, rating: Rating, now: Long): CardSnapshot {
        val steps = CardSnapshot.LEARNING_STEPS_MS
        return when (rating) {
            Rating.AGAIN -> card.copy(
                learningStep = 0,
                dueAt = now + steps[0],
            )
            Rating.HARD -> {
                // Repeat current step (or first step if underflow somehow).
                val s = card.learningStep.coerceIn(0, steps.lastIndex)
                card.copy(dueAt = now + steps[s])
            }
            Rating.GOOD -> {
                val nextStep = card.learningStep + 1
                if (nextStep >= steps.size) {
                    graduateToReview(card, CardSnapshot.GRADUATING_INTERVAL_DAYS, now)
                } else {
                    card.copy(
                        learningStep = nextStep,
                        dueAt = now + steps[nextStep],
                    )
                }
            }
            Rating.EASY -> graduateToReview(
                card,
                CardSnapshot.EASY_GRADUATING_INTERVAL_DAYS,
                now,
            )
        }
    }

    private fun scheduleFromReview(card: CardSnapshot, rating: Rating, now: Long): CardSnapshot {
        return when (rating) {
            Rating.AGAIN -> {
                // Lapse: drop ease, send back to LEARNING at step 0.
                val newEase = (card.ease - 0.2).coerceAtLeast(CardSnapshot.MIN_EASE)
                card.copy(
                    state = CardState.LEARNING,
                    learningStep = 0,
                    ease = newEase,
                    intervalDays = 0.0,
                    lapses = card.lapses + 1,
                    dueAt = now + CardSnapshot.LEARNING_STEPS_MS[0],
                )
            }
            Rating.HARD -> {
                val newEase = (card.ease - 0.15).coerceAtLeast(CardSnapshot.MIN_EASE)
                // Hard multiplier 1.2; never less than current interval + 1 day.
                val newInterval = (card.intervalDays * 1.2).coerceAtLeast(card.intervalDays + 1.0)
                card.copy(
                    ease = newEase,
                    intervalDays = newInterval,
                    reps = card.reps + 1,
                    dueAt = now + (newInterval * CardSnapshot.DAY_MS).toLong(),
                )
            }
            Rating.GOOD -> {
                val newInterval = card.intervalDays * card.ease
                card.copy(
                    intervalDays = newInterval,
                    reps = card.reps + 1,
                    dueAt = now + (newInterval * CardSnapshot.DAY_MS).toLong(),
                )
            }
            Rating.EASY -> {
                val newEase = card.ease + 0.15
                val newInterval = card.intervalDays * card.ease * 1.3
                card.copy(
                    ease = newEase,
                    intervalDays = newInterval,
                    reps = card.reps + 1,
                    dueAt = now + (newInterval * CardSnapshot.DAY_MS).toLong(),
                )
            }
        }
    }

    private fun graduateToReview(
        card: CardSnapshot,
        intervalDays: Double,
        now: Long,
    ): CardSnapshot = card.copy(
        state = CardState.REVIEW,
        intervalDays = intervalDays,
        learningStep = 0,
        reps = card.reps + 1,
        dueAt = now + (intervalDays * CardSnapshot.DAY_MS).toLong(),
    )
}
