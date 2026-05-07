package com.poketrek.moneo.data

import com.poketrek.moneo.srs.CardSnapshot

/**
 * One Korean vocabulary entry. Loaded from bundled JSON in `assets/moneo/`
 * at first launch and merged into the on-disk store. The seed file may be
 * extended over time; new entries are added without disturbing existing
 * card state (matched by [id]).
 */
data class VocabEntry(
    /** Stable id: `"<sourceTag>:<korean>"`. Survives across seed-file edits. */
    val id: String,
    val korean: String,
    val romanization: String,
    val gloss: String,
    val partOfSpeech: String,
    val areaId: String,
    val sourceTag: String,
    val notes: String? = null,
)

/**
 * Persistent SRS state for a single [VocabEntry]. Carries the SM-2
 * [CardSnapshot] plus identity + timestamps useful for the UI.
 */
data class CardRecord(
    val vocabId: String,
    val snapshot: CardSnapshot,
    val createdAt: Long,
    val lastReviewedAt: Long? = null,
    /**
     * User-suspended ("I know this") cards stay in storage but are hidden from
     * review queues and progress counts. Reversible via [MoneoRepository.setSuspended].
     */
    val suspended: Boolean = false,
)

data class AreaProgress(
    val areaId: String,
    val total: Int,
    val newCount: Int,
    val learningCount: Int,
    val reviewCount: Int,
    val dueCount: Int,
)
