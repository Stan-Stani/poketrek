package com.poketrek.moneo.data

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
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
private val KEY_VERBATIM_SENTENCES = booleanPreferencesKey("moneo_verbatim_sentences")
private val KEY_INCLUDE_SPECIES = booleanPreferencesKey("moneo_include_species")
private val KEY_INCLUDE_ETYMOLOGY = booleanPreferencesKey("moneo_include_etymology")

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

    init {
        runBlocking {
            val prefs = context.moneoStore.data.first()
            _enabled.value = prefs[KEY_ENABLED] ?: false
            _targetAreaId.value = prefs[KEY_TARGET_AREA]
            _showRomanization.value = prefs[KEY_SHOW_ROMAJI] ?: true
            _verbatimSentences.value = prefs[KEY_VERBATIM_SENTENCES] ?: true
            _includeSpecies.value = prefs[KEY_INCLUDE_SPECIES] ?: true
            _includeEtymology.value = prefs[KEY_INCLUDE_ETYMOLOGY] ?: false
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

    companion object {
        @Volatile private var instance: MoneoPrefs? = null
        fun get(context: Context): MoneoPrefs = instance ?: synchronized(this) {
            instance ?: MoneoPrefs(context.applicationContext).also { instance = it }
        }
    }
}
