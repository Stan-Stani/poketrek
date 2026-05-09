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
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking

private val Context.moneoStore by preferencesDataStore("moneo_prefs")

private val KEY_ENABLED = booleanPreferencesKey("moneo_enabled")
private val KEY_TARGET_AREA = stringPreferencesKey("moneo_target_area")
private val KEY_SHOW_ROMAJI = booleanPreferencesKey("moneo_show_romanization")
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

    private val _showRomanization = MutableStateFlow(true)
    val showRomanization: StateFlow<Boolean> = _showRomanization.asStateFlow()

    /**
     * Whether to render the example sentence's English gloss on the back of
     * the review card. Defaults on; toggleable from the review header next to
     * the romanization toggle.
     */
    private val _showSentenceGloss = MutableStateFlow(true)
    val showSentenceGloss: StateFlow<Boolean> = _showSentenceGloss.asStateFlow()

    /**
     * Whether the example-sentence card shows a 🔊 speaker button that
     * plays the Korean via Android's built-in TTS. Defaults on; the button
     * is also conditionally hidden when Korean voice data isn't installed
     * (independent of this flag).
     */
    private val _ttsEnabled = MutableStateFlow(true)
    val ttsEnabled: StateFlow<Boolean> = _ttsEnabled.asStateFlow()

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

    init {
        runBlocking {
            val prefs = context.moneoStore.data.first()
            _enabled.value = prefs[KEY_ENABLED] ?: false
            _targetAreaId.value = prefs[KEY_TARGET_AREA]
            _showRomanization.value = prefs[KEY_SHOW_ROMAJI] ?: true
            _showSentenceGloss.value = prefs[KEY_SHOW_SENTENCE_GLOSS] ?: true
            _ttsEnabled.value = prefs[KEY_TTS_ENABLED] ?: true
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
        }
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

    fun setShowRomanization(value: Boolean) {
        _showRomanization.value = value
        scope.launch { context.moneoStore.edit { it[KEY_SHOW_ROMAJI] = value } }
    }

    fun setShowSentenceGloss(value: Boolean) {
        _showSentenceGloss.value = value
        scope.launch { context.moneoStore.edit { it[KEY_SHOW_SENTENCE_GLOSS] = value } }
    }

    fun setTtsEnabled(value: Boolean) {
        _ttsEnabled.value = value
        scope.launch { context.moneoStore.edit { it[KEY_TTS_ENABLED] = value } }
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

    companion object {
        @Volatile private var instance: MoneoPrefs? = null
        fun get(context: Context): MoneoPrefs = instance ?: synchronized(this) {
            instance ?: MoneoPrefs(context.applicationContext).also { instance = it }
        }
    }
}
