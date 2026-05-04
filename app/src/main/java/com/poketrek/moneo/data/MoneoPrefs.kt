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

    init {
        runBlocking {
            val prefs = context.moneoStore.data.first()
            _enabled.value = prefs[KEY_ENABLED] ?: false
            _targetAreaId.value = prefs[KEY_TARGET_AREA]
            _showRomanization.value = prefs[KEY_SHOW_ROMAJI] ?: true
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

    companion object {
        @Volatile private var instance: MoneoPrefs? = null
        fun get(context: Context): MoneoPrefs = instance ?: synchronized(this) {
            instance ?: MoneoPrefs(context.applicationContext).also { instance = it }
        }
    }
}
