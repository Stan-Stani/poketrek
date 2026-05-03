package com.poketrek.step

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.poketrek.emu.MovementGateBudget
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking

private val Context.budgetStore by preferencesDataStore("movement_budget")

private val KEY_BUDGET = intPreferencesKey("budget_tiles")
private val KEY_RATIO = intPreferencesKey("tiles_per_step")
private val KEY_LAST_SENSOR_VALUE = longPreferencesKey("last_sensor_value")
private val KEY_GATE_ENABLED = booleanPreferencesKey("gate_enabled")
private val KEY_DEBUG_HUD = booleanPreferencesKey("debug_hud_visible")

private const val DEFAULT_RATIO = 4
const val MIN_RATIO = 1
const val MAX_RATIO = 16

/**
 * Tracks the player's movement budget — how many in-game tiles they're allowed
 * to walk before they need more real-world steps.
 *
 * One real-world step contributes [tilesPerStep] tiles to [budget]. Phase 3b
 * will call [consumeOneTile] from the native frame callback when a tile
 * transition is detected in the overworld.
 *
 * Process-wide singleton (use [get]) so the foreground StepCounterService and
 * the Activity share state.
 */
class MovementBudget private constructor(private val context: Context) : MovementGateBudget {

    companion object {
        @Volatile private var instance: MovementBudget? = null

        fun get(context: Context): MovementBudget {
            return instance ?: synchronized(this) {
                instance ?: MovementBudget(context.applicationContext).also { instance = it }
            }
        }
    }
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    private val _budget = MutableStateFlow(0)
    override val budget: StateFlow<Int> = _budget.asStateFlow()

    private val _tilesPerStep = MutableStateFlow(DEFAULT_RATIO)
    val tilesPerStep: StateFlow<Int> = _tilesPerStep.asStateFlow()

    private val _gateEnabled = MutableStateFlow(false)
    override val gateEnabled: StateFlow<Boolean> = _gateEnabled.asStateFlow()

    private val _debugHudVisible = MutableStateFlow(false)
    val debugHudVisible: StateFlow<Boolean> = _debugHudVisible.asStateFlow()

    private var lastSensorValue: Long = -1L

    init {
        runBlocking {
            val prefs = context.budgetStore.data.first()
            _budget.value = prefs[KEY_BUDGET] ?: 0
            _tilesPerStep.value = (prefs[KEY_RATIO] ?: DEFAULT_RATIO).coerceIn(MIN_RATIO, MAX_RATIO)
            lastSensorValue = prefs[KEY_LAST_SENSOR_VALUE] ?: -1L
            _gateEnabled.value = prefs[KEY_GATE_ENABLED] ?: false
            _debugHudVisible.value = prefs[KEY_DEBUG_HUD] ?: false
        }
    }

    /**
     * Called by the step source whenever Sensor.TYPE_STEP_COUNTER reports a new
     * cumulative count. Computes a delta from [lastSensorValue], handles reboot
     * (counter resets to 0 → next value is smaller than last), and credits the
     * delta * ratio tiles to the budget.
     */
    fun onSensorValue(cumulativeSteps: Long) {
        val previous = lastSensorValue
        lastSensorValue = cumulativeSteps
        val delta: Long = when {
            previous < 0 -> 0L                       // first ever read, just rebase
            cumulativeSteps < previous -> 0L          // reboot, rebase silently
            else -> cumulativeSteps - previous
        }
        if (delta > 0) {
            addTiles(delta.toInt() * _tilesPerStep.value)
        }
        scope.launch {
            context.budgetStore.edit { it[KEY_LAST_SENSOR_VALUE] = cumulativeSteps }
        }
    }

    /**
     * Debug entry point: adds [realSteps] steps as if the sensor had reported
     * them. Useful for testing on the Android Emulator (which has no
     * TYPE_STEP_COUNTER hardware).
     */
    fun debugAddSteps(realSteps: Int) {
        addTiles(realSteps * _tilesPerStep.value)
    }

    /** Consumes one tile of the budget. Returns false if the budget was 0. */
    override fun consumeOneTile(): Boolean {
        val current = _budget.value
        if (current <= 0) return false
        _budget.value = current - 1
        persistBudget(current - 1)
        return true
    }

    fun setTilesPerStep(value: Int) {
        val clamped = value.coerceIn(MIN_RATIO, MAX_RATIO)
        _tilesPerStep.value = clamped
        scope.launch {
            context.budgetStore.edit { it[KEY_RATIO] = clamped }
        }
    }

    override fun setGateEnabled(value: Boolean) {
        _gateEnabled.value = value
        scope.launch {
            context.budgetStore.edit { it[KEY_GATE_ENABLED] = value }
        }
    }

    fun setDebugHudVisible(value: Boolean) {
        _debugHudVisible.value = value
        scope.launch {
            context.budgetStore.edit { it[KEY_DEBUG_HUD] = value }
        }
    }

    private fun addTiles(tiles: Int) {
        val next = (_budget.value + tiles).coerceAtMost(Int.MAX_VALUE / 2)
        _budget.value = next
        persistBudget(next)
    }

    private fun persistBudget(value: Int) {
        scope.launch {
            context.budgetStore.edit { it[KEY_BUDGET] = value }
        }
    }
}
