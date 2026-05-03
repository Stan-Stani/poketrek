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
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking

private val Context.budgetStore by preferencesDataStore("movement_budget")

private val KEY_BUDGET = intPreferencesKey("budget_tiles")

// Legacy single-int "tiles per step" key, kept only for migration on first
// launch after upgrade. Newer builds use KEY_RATIO_NUM / KEY_RATIO_DEN.
private val KEY_RATIO_LEGACY = intPreferencesKey("tiles_per_step")
private val KEY_RATIO_NUM = intPreferencesKey("tiles_per_step_num")
private val KEY_RATIO_DEN = intPreferencesKey("tiles_per_step_den")
private val KEY_STEP_CARRY = intPreferencesKey("step_carry_remainder")

private val KEY_LAST_SENSOR_VALUE = longPreferencesKey("last_sensor_value")
private val KEY_GATE_ENABLED = booleanPreferencesKey("gate_enabled")
private val KEY_DEBUG_HUD = booleanPreferencesKey("debug_hud_visible")
private val KEY_HAPTIC_ON_STEP = booleanPreferencesKey("haptic_on_step")

private const val DEFAULT_RATIO_NUM = 4
private const val DEFAULT_RATIO_DEN = 1
const val MIN_RATIO_PART = 1
const val MAX_RATIO_PART = 32

/**
 * Computes how many whole tiles to credit for [deltaSteps] real-world steps
 * given a fractional ratio of [num]/[den] tiles per step and a leftover
 * [carryIn] remainder from previous calls. Returns (tilesAwarded, carryOut).
 *
 * Pure function — pulled out of MovementBudget so it can be tested without
 * an Android Context.
 */
internal fun creditTiles(
    deltaSteps: Long,
    num: Int,
    den: Int,
    carryIn: Int,
): Pair<Long, Int> {
    require(num >= 1 && den >= 1) { "ratio parts must be >= 1" }
    if (deltaSteps <= 0) return 0L to carryIn
    val totalCredit = carryIn.toLong() + deltaSteps * num.toLong()
    val tilesAwarded = totalCredit / den
    val carryOut = (totalCredit % den).toInt()
    return tilesAwarded to carryOut
}

/**
 * Tracks the player's movement budget — how many in-game tiles they're allowed
 * to walk before they need more real-world steps.
 *
 * The budget is credited at a fractional ratio of [tilesPerStepNum] /
 * [tilesPerStepDen] tiles per real-world step. Examples:
 *   - 4/1: easy, 1 step = 4 tiles (default)
 *   - 1/1: realistic, 1 step = 1 tile
 *   - 1/2: hard, 2 steps required for 1 tile
 *
 * Sub-1 ratios mean a single step often credits zero tiles; the leftover
 * lives in [stepCarry] and combines with the next step's contribution. The
 * carry is persisted across launches and reset on ratio change.
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

    private val _tilesPerStepNum = MutableStateFlow(DEFAULT_RATIO_NUM)
    val tilesPerStepNum: StateFlow<Int> = _tilesPerStepNum.asStateFlow()

    private val _tilesPerStepDen = MutableStateFlow(DEFAULT_RATIO_DEN)
    val tilesPerStepDen: StateFlow<Int> = _tilesPerStepDen.asStateFlow()

    private val _gateEnabled = MutableStateFlow(false)
    override val gateEnabled: StateFlow<Boolean> = _gateEnabled.asStateFlow()

    private val _debugHudVisible = MutableStateFlow(false)
    val debugHudVisible: StateFlow<Boolean> = _debugHudVisible.asStateFlow()

    private val _hapticOnStep = MutableStateFlow(true)
    val hapticOnStep: StateFlow<Boolean> = _hapticOnStep.asStateFlow()

    /**
     * Fires (tilesAwarded) every time the budget is credited. Subscribers
     * (e.g. the haptic vibrator in StepCounterService, future HUD flash
     * animations, step-history graph) consume this without having to poll
     * the budget StateFlow.
     */
    private val _creditedTiles = MutableSharedFlow<Int>(extraBufferCapacity = 16)
    val creditedTiles: SharedFlow<Int> = _creditedTiles.asSharedFlow()

    private var lastSensorValue: Long = -1L
    private var stepCarry: Int = 0

    init {
        runBlocking {
            val prefs = context.budgetStore.data.first()
            _budget.value = prefs[KEY_BUDGET] ?: 0
            val legacy = prefs[KEY_RATIO_LEGACY]
            val num = prefs[KEY_RATIO_NUM] ?: legacy ?: DEFAULT_RATIO_NUM
            val den = prefs[KEY_RATIO_DEN] ?: DEFAULT_RATIO_DEN
            _tilesPerStepNum.value = num.coerceIn(MIN_RATIO_PART, MAX_RATIO_PART)
            _tilesPerStepDen.value = den.coerceIn(MIN_RATIO_PART, MAX_RATIO_PART)
            stepCarry = (prefs[KEY_STEP_CARRY] ?: 0).coerceAtLeast(0)
            lastSensorValue = prefs[KEY_LAST_SENSOR_VALUE] ?: -1L
            _gateEnabled.value = prefs[KEY_GATE_ENABLED] ?: false
            _debugHudVisible.value = prefs[KEY_DEBUG_HUD] ?: false
            _hapticOnStep.value = prefs[KEY_HAPTIC_ON_STEP] ?: true
        }
    }

    /**
     * Called by the step source whenever Sensor.TYPE_STEP_COUNTER reports a new
     * cumulative count. Computes a delta from [lastSensorValue], handles reboot
     * (counter resets to 0 → next value is smaller than last), and credits the
     * delta * ratio tiles to the budget — carrying the fractional remainder.
     */
    fun onSensorValue(cumulativeSteps: Long) {
        val previous = lastSensorValue
        lastSensorValue = cumulativeSteps
        val delta: Long = when {
            previous < 0 -> 0L                       // first ever read, just rebase
            cumulativeSteps < previous -> 0L          // reboot, rebase silently
            else -> cumulativeSteps - previous
        }
        creditAndPersist(delta)
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
        if (realSteps <= 0) return
        creditAndPersist(realSteps.toLong())
    }

    private fun creditAndPersist(deltaSteps: Long) {
        if (deltaSteps <= 0) return
        val (tiles, newCarry) = creditTiles(
            deltaSteps,
            _tilesPerStepNum.value,
            _tilesPerStepDen.value,
            stepCarry,
        )
        val carryChanged = newCarry != stepCarry
        stepCarry = newCarry
        if (tiles > 0) {
            addTiles(tiles.toInt().coerceAtLeast(0))
        } else if (carryChanged) {
            persistCarry(newCarry)
        }
    }

    /** Consumes one tile of the budget. Returns false if the budget was 0. */
    override fun consumeOneTile(): Boolean {
        val current = _budget.value
        if (current <= 0) return false
        _budget.value = current - 1
        persistBudget(current - 1)
        return true
    }

    /**
     * Sets the credit ratio to [num] tiles per [den] real-world steps. Resets
     * the carry remainder so a switch from e.g. 1:8 → 8:1 doesn't drop a
     * stale partial credit.
     */
    fun setRatio(num: Int, den: Int) {
        val n = num.coerceIn(MIN_RATIO_PART, MAX_RATIO_PART)
        val d = den.coerceIn(MIN_RATIO_PART, MAX_RATIO_PART)
        if (n == _tilesPerStepNum.value && d == _tilesPerStepDen.value) return
        _tilesPerStepNum.value = n
        _tilesPerStepDen.value = d
        stepCarry = 0
        scope.launch {
            context.budgetStore.edit {
                it[KEY_RATIO_NUM] = n
                it[KEY_RATIO_DEN] = d
                it[KEY_STEP_CARRY] = 0
                it.remove(KEY_RATIO_LEGACY)
            }
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

    fun setHapticOnStep(value: Boolean) {
        _hapticOnStep.value = value
        scope.launch {
            context.budgetStore.edit { it[KEY_HAPTIC_ON_STEP] = value }
        }
    }

    private fun addTiles(tiles: Int) {
        val next = (_budget.value + tiles).coerceAtMost(Int.MAX_VALUE / 2)
        _budget.value = next
        _creditedTiles.tryEmit(tiles)
        val carryToWrite = stepCarry
        scope.launch {
            context.budgetStore.edit {
                it[KEY_BUDGET] = next
                it[KEY_STEP_CARRY] = carryToWrite
            }
        }
    }

    private fun persistBudget(value: Int) {
        scope.launch {
            context.budgetStore.edit { it[KEY_BUDGET] = value }
        }
    }

    private fun persistCarry(value: Int) {
        scope.launch {
            context.budgetStore.edit { it[KEY_STEP_CARRY] = value }
        }
    }
}
