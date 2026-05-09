package com.poketrek.moneo.data

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking

private val Context.moneoStore by preferencesDataStore("moneo_prefs")

private val KEY_ENABLED = booleanPreferencesKey("moneo_enabled")
private val KEY_TARGET_AREA = stringPreferencesKey("moneo_target_area")
private val KEY_SHOW_SENTENCE_GLOSS = booleanPreferencesKey("moneo_show_sentence_gloss")
private val KEY_TTS_ENABLED = booleanPreferencesKey("moneo_tts_enabled")
private val KEY_TTS_AUTO_REVEAL = booleanPreferencesKey("moneo_tts_auto_reveal")
private val KEY_TTS_AUTO_FRONT = booleanPreferencesKey("moneo_tts_auto_front")
private val KEY_TTS_RATE_PCT = intPreferencesKey("moneo_tts_rate_pct")
private val KEY_MUTE_GAME_IN_REVIEW = booleanPreferencesKey("moneo_mute_game_in_review")
private val KEY_VERBATIM_SENTENCES = booleanPreferencesKey("moneo_verbatim_sentences")
private val KEY_INCLUDE_SPECIES = booleanPreferencesKey("moneo_include_species")
private val KEY_INCLUDE_ETYMOLOGY = booleanPreferencesKey("moneo_include_etymology")
private val KEY_AREA_GATE_ENABLED = booleanPreferencesKey("moneo_area_gate_enabled")
private val KEY_AREA_GATE_THRESHOLD_PCT = intPreferencesKey("moneo_area_gate_threshold_pct")
private val KEY_DIRECTION = stringPreferencesKey("moneo_direction")
private val KEY_TTS_LANGUAGE = stringPreferencesKey("moneo_tts_language")

/**
 * Which way the flashcards face. Default [KO_TO_EN] preserves the original
 * Korean-learner-of-Korean experience; [EN_TO_KO] flips the cards so a Korean
 * speaker can study English using the same vocab/sentence corpus reversed.
 */
enum class FlashcardDirection {
    KO_TO_EN, EN_TO_KO;
    companion object {
        fun fromStored(value: String?): FlashcardDirection =
            entries.firstOrNull { it.name == value } ?: KO_TO_EN
    }
}

/**
 * The TTS voice used when the speaker button is tapped (and for auto-play).
 * Independent from [FlashcardDirection] so a user can study reversed cards
 * but still hear the *original* language read aloud.
 *
 * [OFF] hides the speaker button and disables all auto-play, replacing the
 * legacy `tts_enabled = false` boolean.
 */
enum class TtsLanguage {
    KOREAN, ENGLISH, OFF;
    companion object {
        fun fromStored(value: String?): TtsLanguage? =
            value?.let { v -> entries.firstOrNull { it.name == v } }

        fun defaultFor(direction: FlashcardDirection): TtsLanguage = when (direction) {
            FlashcardDirection.KO_TO_EN -> KOREAN
            FlashcardDirection.EN_TO_KO -> ENGLISH
        }
    }
}

/**
 * The effective TTS language: the user's explicit override if set, otherwise
 * the default for the current direction.
 */
fun effectiveTtsLanguage(direction: FlashcardDirection, override: TtsLanguage?): TtsLanguage =
    override ?: TtsLanguage.defaultFor(direction)

/**
 * One-shot migration from the legacy `tts_enabled` boolean. Returns the
 * value that should be stored as [KEY_TTS_LANGUAGE] (or null to leave it
 * unset and inherit the direction-default).
 *
 * Rule: if no explicit override is recorded yet AND the legacy flag was
 * persisted as `false`, treat it as "user disabled TTS" → [TtsLanguage.OFF].
 * Any other case (legacy not persisted, legacy true, override already set)
 * leaves the override as-is.
 */
fun migrateTtsLegacy(legacyEnabled: Boolean?, existingOverride: TtsLanguage?): TtsLanguage? {
    if (existingOverride != null) return existingOverride
    if (legacyEnabled == false) return TtsLanguage.OFF
    return null
}

const val DEFAULT_AREA_GATE_THRESHOLD_PCT = 80
const val MIN_AREA_GATE_THRESHOLD_PCT = 0
const val MAX_AREA_GATE_THRESHOLD_PCT = 100

const val DEFAULT_TTS_RATE_PCT = 100
const val MIN_TTS_RATE_PCT = 50
const val MAX_TTS_RATE_PCT = 200

/**
 * Moneo's user preferences. Intentionally separate from [MovementBudget]'s
 * DataStore so the two features remain forkable.
 */
class MoneoPrefs private constructor(private val context: Context) {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    private val _enabled = MutableStateFlow(false)
    val enabled: StateFlow<Boolean> = _enabled.asStateFlow()

    private val _targetAreaId = MutableStateFlow<String?>(null)
    val targetAreaId: StateFlow<String?> = _targetAreaId.asStateFlow()

    /**
     * Whether to render the example sentence's English gloss on the back of
     * the review card. Defaults on; toggleable from the review header.
     */
    private val _showSentenceGloss = MutableStateFlow(true)
    val showSentenceGloss: StateFlow<Boolean> = _showSentenceGloss.asStateFlow()

    /** Auto-speak the example sentence when the back of the card is revealed. */
    private val _ttsAutoPlayReveal = MutableStateFlow(false)
    val ttsAutoPlayReveal: StateFlow<Boolean> = _ttsAutoPlayReveal.asStateFlow()

    /** Auto-speak the headword when a new card is shown (front side). */
    private val _ttsAutoPlayFront = MutableStateFlow(false)
    val ttsAutoPlayFront: StateFlow<Boolean> = _ttsAutoPlayFront.asStateFlow()

    /** Speech rate as percent of normal (50–200; 100 = 1.0x). */
    private val _ttsRatePct = MutableStateFlow(DEFAULT_TTS_RATE_PCT)
    val ttsRatePct: StateFlow<Int> = _ttsRatePct.asStateFlow()

    /**
     * When the Moneo review overlay is open, fully mute the game's
     * AudioTrack. Independent of TTS — the duck-during-TTS behavior is
     * always-on regardless of this flag.
     */
    private val _muteGameInReview = MutableStateFlow(false)
    val muteGameInReview: StateFlow<Boolean> = _muteGameInReview.asStateFlow()

    /**
     * Toggle for the example-sentence source on the review screen.
     *  - `true`  → ROM verbatim (`sentences-ko-rom.json`); authentic but may spoil dialog/Pokédex.
     *  - `false` → hand-written study sentences (`sentences-ko-study.json`); plain TOPIK-1 phrasing, no plot leaks.
     * Defaults to `true` to match the Phase 3 ship behavior.
     */
    private val _verbatimSentences = MutableStateFlow(true)
    val verbatimSentences: StateFlow<Boolean> = _verbatimSentences.asStateFlow()

    private val _includeSpecies = MutableStateFlow(true)
    val includeSpecies: StateFlow<Boolean> = _includeSpecies.asStateFlow()

    /**
     * Etymology root cards harvested from species-name pun explanations
     * (e.g. 곰 from 링곰, 거북 from 꼬부기). Default off because it's an
     * opt-in tangential vocab boost, not core game vocab.
     */
    private val _includeEtymology = MutableStateFlow(false)
    val includeEtymology: StateFlow<Boolean> = _includeEtymology.asStateFlow()

    /**
     * Hard area gate: when on, MovementGate refuses to enter a downstream area
     * until the upstream area's review maturity meets [areaGateThresholdPct].
     * Default off — the player should opt in once they've built up some review
     * history, otherwise the very first map transition would be blocked.
     */
    private val _areaGateEnabled = MutableStateFlow(false)
    val areaGateEnabled: StateFlow<Boolean> = _areaGateEnabled.asStateFlow()

    private val _areaGateThresholdPct = MutableStateFlow(DEFAULT_AREA_GATE_THRESHOLD_PCT)
    val areaGateThresholdPct: StateFlow<Int> = _areaGateThresholdPct.asStateFlow()

    /**
     * Flashcard display direction. KO_TO_EN (default) shows Korean on the
     * front; EN_TO_KO flips for Korean native speakers learning English.
     */
    private val _direction = MutableStateFlow(FlashcardDirection.KO_TO_EN)
    val direction: StateFlow<FlashcardDirection> = _direction.asStateFlow()

    /**
     * Explicit TTS-language override. `null` means "follow the direction
     * default" (KO_TO_EN → KOREAN, EN_TO_KO → ENGLISH). Use
     * [effectiveTtsLanguage] when consuming.
     */
    private val _ttsLanguageOverride = MutableStateFlow<TtsLanguage?>(null)
    val ttsLanguageOverride: StateFlow<TtsLanguage?> = _ttsLanguageOverride.asStateFlow()

    /** Derived: the actual TTS language that should be used right now. */
    val effectiveTtsLanguage: StateFlow<TtsLanguage>

    init {
        runBlocking {
            val prefs = context.moneoStore.data.first()
            _enabled.value = prefs[KEY_ENABLED] ?: false
            _targetAreaId.value = prefs[KEY_TARGET_AREA]
            _showSentenceGloss.value = prefs[KEY_SHOW_SENTENCE_GLOSS] ?: true
            _ttsAutoPlayReveal.value = prefs[KEY_TTS_AUTO_REVEAL] ?: false
            _ttsAutoPlayFront.value = prefs[KEY_TTS_AUTO_FRONT] ?: false
            _ttsRatePct.value =
                (prefs[KEY_TTS_RATE_PCT] ?: DEFAULT_TTS_RATE_PCT)
                    .coerceIn(MIN_TTS_RATE_PCT, MAX_TTS_RATE_PCT)
            _muteGameInReview.value = prefs[KEY_MUTE_GAME_IN_REVIEW] ?: false
            _verbatimSentences.value = prefs[KEY_VERBATIM_SENTENCES] ?: true
            _includeSpecies.value = prefs[KEY_INCLUDE_SPECIES] ?: true
            _includeEtymology.value = prefs[KEY_INCLUDE_ETYMOLOGY] ?: false
            _areaGateEnabled.value = prefs[KEY_AREA_GATE_ENABLED] ?: false
            _areaGateThresholdPct.value =
                (prefs[KEY_AREA_GATE_THRESHOLD_PCT] ?: DEFAULT_AREA_GATE_THRESHOLD_PCT)
                    .coerceIn(MIN_AREA_GATE_THRESHOLD_PCT, MAX_AREA_GATE_THRESHOLD_PCT)
            _direction.value = FlashcardDirection.fromStored(prefs[KEY_DIRECTION])
            val storedOverride = TtsLanguage.fromStored(prefs[KEY_TTS_LANGUAGE])
            val migrated = migrateTtsLegacy(prefs[KEY_TTS_ENABLED], storedOverride)
            _ttsLanguageOverride.value = migrated
            // Persist the migration so future launches don't reapply the legacy rule.
            if (migrated != null && storedOverride == null) {
                scope.launch {
                    context.moneoStore.edit { it[KEY_TTS_LANGUAGE] = migrated.name }
                }
            }
        }
        effectiveTtsLanguage = combine(_direction, _ttsLanguageOverride) { dir, override ->
            effectiveTtsLanguage(dir, override)
        }.stateIn(
            scope,
            SharingStarted.Eagerly,
            effectiveTtsLanguage(_direction.value, _ttsLanguageOverride.value),
        )
    }

    fun setEnabled(value: Boolean) {
        _enabled.value = value
        scope.launch { context.moneoStore.edit { it[KEY_ENABLED] = value } }
    }

    fun setTargetAreaId(areaId: String?) {
        _targetAreaId.value = areaId
        scope.launch {
            context.moneoStore.edit { prefs ->
                if (areaId == null) prefs.remove(KEY_TARGET_AREA)
                else prefs[KEY_TARGET_AREA] = areaId
            }
        }
    }

    fun setShowSentenceGloss(value: Boolean) {
        _showSentenceGloss.value = value
        scope.launch { context.moneoStore.edit { it[KEY_SHOW_SENTENCE_GLOSS] = value } }
    }

    fun setTtsAutoPlayReveal(value: Boolean) {
        _ttsAutoPlayReveal.value = value
        scope.launch { context.moneoStore.edit { it[KEY_TTS_AUTO_REVEAL] = value } }
    }

    fun setTtsAutoPlayFront(value: Boolean) {
        _ttsAutoPlayFront.value = value
        scope.launch { context.moneoStore.edit { it[KEY_TTS_AUTO_FRONT] = value } }
    }

    fun setTtsRatePct(value: Int) {
        val v = value.coerceIn(MIN_TTS_RATE_PCT, MAX_TTS_RATE_PCT)
        if (v == _ttsRatePct.value) return
        _ttsRatePct.value = v
        scope.launch { context.moneoStore.edit { it[KEY_TTS_RATE_PCT] = v } }
    }

    fun setMuteGameInReview(value: Boolean) {
        if (value == _muteGameInReview.value) return
        _muteGameInReview.value = value
        scope.launch { context.moneoStore.edit { it[KEY_MUTE_GAME_IN_REVIEW] = value } }
    }

    fun setVerbatimSentences(value: Boolean) {
        _verbatimSentences.value = value
        scope.launch { context.moneoStore.edit { it[KEY_VERBATIM_SENTENCES] = value } }
    }

    fun setIncludeSpecies(value: Boolean) {
        _includeSpecies.value = value
        scope.launch { context.moneoStore.edit { it[KEY_INCLUDE_SPECIES] = value } }
    }

    fun setIncludeEtymology(value: Boolean) {
        _includeEtymology.value = value
        scope.launch { context.moneoStore.edit { it[KEY_INCLUDE_ETYMOLOGY] = value } }
    }

    fun setAreaGateEnabled(value: Boolean) {
        if (value == _areaGateEnabled.value) return
        _areaGateEnabled.value = value
        scope.launch { context.moneoStore.edit { it[KEY_AREA_GATE_ENABLED] = value } }
    }

    fun setAreaGateThresholdPct(value: Int) {
        val v = value.coerceIn(MIN_AREA_GATE_THRESHOLD_PCT, MAX_AREA_GATE_THRESHOLD_PCT)
        if (v == _areaGateThresholdPct.value) return
        _areaGateThresholdPct.value = v
        scope.launch { context.moneoStore.edit { it[KEY_AREA_GATE_THRESHOLD_PCT] = v } }
    }

    fun setDirection(value: FlashcardDirection) {
        if (value == _direction.value) return
        _direction.value = value
        scope.launch { context.moneoStore.edit { it[KEY_DIRECTION] = value.name } }
    }

    /**
     * Pin TTS to a specific language regardless of [direction]. Pass `null`
     * (or call [clearTtsLanguageOverride]) to revert to the direction default.
     */
    fun setTtsLanguage(value: TtsLanguage?) {
        if (value == _ttsLanguageOverride.value) return
        _ttsLanguageOverride.value = value
        scope.launch {
            context.moneoStore.edit { prefs ->
                if (value == null) prefs.remove(KEY_TTS_LANGUAGE)
                else prefs[KEY_TTS_LANGUAGE] = value.name
            }
        }
    }

    fun clearTtsLanguageOverride() = setTtsLanguage(null)

    companion object {
        @Volatile private var instance: MoneoPrefs? = null
        fun get(context: Context): MoneoPrefs = instance ?: synchronized(this) {
            instance ?: MoneoPrefs(context.applicationContext).also { instance = it }
        }
    }
}
