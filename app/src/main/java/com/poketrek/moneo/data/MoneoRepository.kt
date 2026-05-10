package com.poketrek.moneo.data

import com.poketrek.moneo.srs.CardState
import com.poketrek.moneo.srs.Rating
import com.poketrek.moneo.srs.Sm2
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * Public API for the Moneo data layer. Holds vocab + card state in memory
 * (sourced from [SeedLoader] + [MoneoCardStore]) and exposes derived flows
 * for the UI.
 *
 * Lifecycle: a single instance is created by [com.poketrek.moneo.MoneoModule]
 * during activity creation and lives for the process lifetime.
 */
class MoneoRepository(
    private val store: MoneoCardStore,
    initialVocab: List<VocabEntry>,
    initialAreas: List<Area>,
    initialSentencesRom: List<SentenceEntry> = emptyList(),
    initialSentencesStudy: List<SentenceEntry> = emptyList(),
    private val now: () -> Long = { System.currentTimeMillis() },
) {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    private val _vocab = MutableStateFlow(initialVocab.associateBy { it.id })
    val vocab: StateFlow<Map<String, VocabEntry>> = _vocab.asStateFlow()

    private val _areas = MutableStateFlow(initialAreas)
    val areas: StateFlow<List<Area>> = _areas.asStateFlow()

    private val _cards = MutableStateFlow<Map<String, CardRecord>>(emptyMap())
    val cards: StateFlow<Map<String, CardRecord>> = _cards.asStateFlow()

    /**
     * Source tags that should be excluded from review surfaces. Driven by user
     * preferences (e.g. opting out of Pokemon-name flashcards). Vocab entries
     * with a matching [VocabEntry.sourceTag] are filtered from [vocabForArea],
     * [nextDueCard], [totalDueCount], [dueCountForArea], and area progress.
     * Default empty so all decks are visible.
     */
    private val _excludedSourceTags = MutableStateFlow<Set<String>>(emptySet())
    val excludedSourceTags: StateFlow<Set<String>> = _excludedSourceTags.asStateFlow()

    fun setExcludedSourceTags(tags: Set<String>) {
        _excludedSourceTags.value = tags
    }

    /** Sentences indexed by [SentenceEntry.vocabId]; multiple per vocab allowed. */
    private val sentencesRomByVocab: Map<String, List<SentenceEntry>> = initialSentencesRom.groupBy { it.vocabId }
    private val sentencesStudyByVocab: Map<String, List<SentenceEntry>> = initialSentencesStudy.groupBy { it.vocabId }

    /**
     * Returns up to one example sentence for the given vocab id.
     *
     * [verbatim] selects the source: true = ROM-rip text (may spoil dialog),
     * false = hand-written study sentences. When [preferAreaId] is supplied,
     * picks the first sentence whose areaId matches; falls back to any
     * sentence for the vocab in that source.
     */
    fun sentenceFor(
        vocabId: String,
        preferAreaId: String? = null,
        verbatim: Boolean = true,
    ): SentenceEntry? {
        val map = if (verbatim) sentencesRomByVocab else sentencesStudyByVocab
        val all = map[vocabId] ?: return null
        if (preferAreaId != null) {
            all.firstOrNull { it.areaId == preferAreaId }?.let { return it }
        }
        return all.firstOrNull()
    }

    init {
        // Make sure every seed entry has a card row. Idempotent on repeat launch.
        store.ensureExists(initialVocab.map { it.id }, now())
        _cards.value = store.all().associateBy { it.vocabId }
    }

    /**
     * Vocab visible while the player is in [areaId].
     *
     * Matches a card if EITHER:
     *  - its primary [VocabEntry.areaId] equals the queried area (the
     *    canonical "home area" — typically firstAreaEncountered), OR
     *  - the queried area appears in [VocabEntry.areasReferenced] (the
     *    full set of canonical areas where the lemma surfaces in ROM
     *    dialog/script). Cards shipped before the attribution pipeline
     *    have an empty list, so the second clause is a no-op for them.
     *
     * Filters out cards whose [VocabEntry.sourceTag] is in
     * [excludedSourceTags] (e.g. user opted out of Pokémon-name cards).
     */
    fun vocabForArea(areaId: String): List<VocabEntry> {
        val excluded = _excludedSourceTags.value
        return _vocab.value.values.filter {
            (it.areaId == areaId || areaId in it.areasReferenced) &&
                it.sourceTag !in excluded
        }
    }

    /** Vocab IDs visible after applying [excludedSourceTags]. Used by due-count helpers. */
    private fun visibleVocabIds(): Set<String> {
        val excluded = _excludedSourceTags.value
        if (excluded.isEmpty()) return _vocab.value.keys
        return _vocab.value.values.filter { it.sourceTag !in excluded }.map { it.id }.toSet()
    }

    fun areaProgress(areaId: String): StateFlow<AreaProgress> {
        // Backed by combining the cards flow with the vocab snapshot. Since
        // vocab only changes when seeds are reloaded (rare), it's fine to
        // snapshot it eagerly.
        val derived = MutableStateFlow(computeAreaProgress(areaId))
        scope.launch {
            _cards.collect { _ -> derived.value = computeAreaProgress(areaId) }
        }
        return derived.asStateFlow()
    }

    private fun computeAreaProgress(areaId: String): AreaProgress {
        val vocab = vocabForArea(areaId)
        val ids = vocab.map { it.id }.toSet()
        val cards = _cards.value.values.filter { it.vocabId in ids && !it.suspended }
        val n = now()
        val newCount = cards.count { it.snapshot.state == CardState.NEW }
        val learning = cards.count { it.snapshot.state == CardState.LEARNING }
        val review = cards.count { it.snapshot.state == CardState.REVIEW }
        // NEW cards count as due (they need first exposure); LEARNING/REVIEW
        // count when their next-due timestamp has elapsed.
        val dueCount = cards.count { rec ->
            rec.snapshot.state == CardState.NEW || rec.snapshot.dueAt <= n
        }
        return AreaProgress(
            areaId = areaId,
            total = vocab.size,
            newCount = newCount,
            learningCount = learning,
            reviewCount = review,
            dueCount = dueCount,
        )
    }

    /**
     * Pick the next due card for [areaId]. Returns null if no cards are due
     * right now. Selection priority:
     *   1. LEARNING cards whose due time has passed (oldest-due first)
     *   2. REVIEW cards due today
     *   3. NEW cards (limited per session via the caller's pacing if needed)
     */
    fun nextDueCard(areaId: String, nowMs: Long = now()): Pair<CardRecord, VocabEntry>? {
        val vocab = vocabForArea(areaId).associateBy { it.id }
        if (vocab.isEmpty()) return null
        val cards = _cards.value.values.filter { it.vocabId in vocab.keys && !it.suspended }

        val learning = cards.filter { it.snapshot.state == CardState.LEARNING && it.snapshot.dueAt <= nowMs }
            .sortedBy { it.snapshot.dueAt }
        if (learning.isNotEmpty()) {
            val rec = learning.first()
            return rec to (vocab[rec.vocabId] ?: return null)
        }
        val review = cards.filter { it.snapshot.state == CardState.REVIEW && it.snapshot.dueAt <= nowMs }
            .sortedBy { it.snapshot.dueAt }
        if (review.isNotEmpty()) {
            val rec = review.first()
            return rec to (vocab[rec.vocabId] ?: return null)
        }
        val news = cards.filter { it.snapshot.state == CardState.NEW }
            .sortedBy { it.createdAt }
        if (news.isNotEmpty()) {
            val rec = news.first()
            return rec to (vocab[rec.vocabId] ?: return null)
        }
        return null
    }

    /**
     * Apply [rating] to [vocabId]; persists the new card state and updates
     * the in-memory flow.
     */
    fun grade(vocabId: String, rating: Rating, nowMs: Long = now()) {
        val current = _cards.value[vocabId] ?: return
        val nextSnap = Sm2.schedule(current.snapshot, rating, nowMs)
        val updated = current.copy(snapshot = nextSnap, lastReviewedAt = nowMs)
        store.put(updated)
        _cards.value = _cards.value + (vocabId to updated)
    }

    /** Total cards due across all areas at [nowMs]. NEW cards always count as due. */
    fun totalDueCount(nowMs: Long = now()): Int {
        val visible = visibleVocabIds()
        return _cards.value.values.count { rec ->
            rec.vocabId in visible && !rec.suspended &&
                (rec.snapshot.state == CardState.NEW || rec.snapshot.dueAt <= nowMs)
        }
    }

    /** Cards due in the player's currently-selected target area. */
    fun dueCountForArea(areaId: String, nowMs: Long = now()): Int {
        val ids = vocabForArea(areaId).map { it.id }.toSet()
        return _cards.value.values.count { rec ->
            rec.vocabId in ids && !rec.suspended &&
                (rec.snapshot.state == CardState.NEW || rec.snapshot.dueAt <= nowMs)
        }
    }

    /**
     * Mark [vocabId] as user-suspended ("I know this") or restore it. Suspended
     * cards are hidden from review queues and progress counts but kept in the
     * store so the action is reversible (e.g. via the snackbar Undo).
     */
    fun setSuspended(vocabId: String, suspended: Boolean) {
        val current = _cards.value[vocabId] ?: return
        if (current.suspended == suspended) return
        val updated = current.copy(suspended = suspended)
        store.put(updated)
        _cards.value = _cards.value + (vocabId to updated)
    }

    /**
     * Fraction of cards in [areaId] considered "mature" — i.e. cards in the
     * REVIEW state or user-suspended (the user vouched they know it). Used
     * by the area-gate to decide whether the player may cross into a higher
     * ordinal area in-game.
     *
     * Returns 1.0 for areas with no visible vocab (vacuously cleared) so
     * empty/unused areas never block progression.
     */
    fun maturityPct(areaId: String): Float {
        val ids = vocabForArea(areaId).map { it.id }.toSet()
        if (ids.isEmpty()) return 1f
        val cards = _cards.value.values.filter { it.vocabId in ids }
        if (cards.isEmpty()) return 1f
        val mature = cards.count { it.suspended || it.snapshot.state == CardState.REVIEW }
        return mature.toFloat() / cards.size
    }

    /** Wipe all SRS state. Used by debug actions. */
    fun resetAllProgress() {
        store.clear()
        store.ensureExists(_vocab.value.keys, now())
        _cards.value = store.all().associateBy { it.vocabId }
    }
}