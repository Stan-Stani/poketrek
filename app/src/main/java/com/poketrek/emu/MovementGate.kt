package com.poketrek.emu

import kotlinx.coroutines.flow.StateFlow

/**
 * Minimal surface MovementGate needs from the budget. Letting the gate take
 * an interface (instead of the concrete MovementBudget, which depends on a
 * Context + DataStore) keeps the gate testable on the plain JVM.
 */
interface MovementGateBudget {
    val budget: StateFlow<Int>
    val gateEnabled: StateFlow<Boolean>
    fun setGateEnabled(value: Boolean)
    fun consumeOneTile(): Boolean
}

/**
 * Decision describing whether the area-gate should currently mask a press.
 * Returned by [MoneoAreaGate.evaluate] each frame. When [shouldBlock] is true
 * the press direction(s) returned by [blockedDirMask] should be cleared from
 * the key bitmask. The remaining fields are used by the HUD lock chip.
 */
data class AreaGateDecision(
    /** True if the gate should mask one or more direction bits this frame. */
    val shouldBlock: Boolean,
    /** GbaKey direction-bit mask to clear from the raw keys. */
    val blockedDirMask: Int,
    /** Destination area being blocked (for HUD), or null if not blocking. */
    val destArea: String? = null,
    /** Current maturity (0..1) of that area, for HUD display. */
    val maturityFraction: Float = 0f,
    /** Threshold (0..1) being applied, for HUD display. */
    val thresholdFraction: Float = 0f,
) {
    companion object {
        val NONE = AreaGateDecision(shouldBlock = false, blockedDirMask = 0)
    }
}

/**
 * Hard area-gate hook consulted by [MovementGate.process] each frame.
 * Tells the gate whether the *currently-pressed* direction(s) should be
 * masked because they would carry the player across into a Moneo Area whose
 * vocab maturity is below the user's threshold.
 *
 * Implementations are expected to:
 *  - Look up boundaries at (bank, mapId, x, y) via MapBoundaryLookup.
 *  - Compare destination-area maturity to the configured threshold.
 *  - Honour the user's enable toggle.
 *
 * Kept as an interface so MovementGateTest can run without an Android Context.
 */
interface MoneoAreaGate {
    /**
     * Evaluate the area-gate at the current player position with the current
     * raw key bits. The implementation may mark the decision as 'blocking'
     * even if no direction is currently pressed (e.g. the player is standing
     * on a warp tile), but the gate will only effectively mask whichever
     * directions [AreaGateDecision.blockedDirMask] selects.
     */
    fun evaluate(rawKeys: Int, snapshot: LeafGreenRam.Snapshot): AreaGateDecision

    /**
     * StateFlow exposing the latest decision so the HUD can render a lock
     * chip without re-running the lookup itself. Defaults to NONE.
     */
    val lastDecision: StateFlow<AreaGateDecision>

    companion object {
        /** No-op gate used for ROMs/configs where the area-gate is disabled. */
        val DISABLED: MoneoAreaGate = NoopMoneoAreaGate
    }
}

private object NoopMoneoAreaGate : MoneoAreaGate {
    override fun evaluate(rawKeys: Int, snapshot: LeafGreenRam.Snapshot): AreaGateDecision =
        AreaGateDecision.NONE
    override val lastDecision: StateFlow<AreaGateDecision> =
        kotlinx.coroutines.flow.MutableStateFlow(AreaGateDecision.NONE)
}

/**
 * The actual step-gating logic. Sits between the emulator's frame loop and
 * mGBA's setKeys: every frame, [process] (a) detects player tile transitions
 * by diffing the LeafGreen RAM snapshot vs the previous frame and consumes
 * one tile from the budget when one occurs, and (b) masks the direction
 * bits out of the key bitmask when the gate is enabled and the budget is
 * exhausted.
 *
 * The decrement rule mirrors the plan: only count a step if (X or Y changed)
 * AND (map ID unchanged — otherwise we're warping through a door) AND
 * (a direction was held last frame — so cutscenes/scripted movement and
 * ledge hops/ice tiles don't get charged).
 *
 * The gate-enabled flag and current budget live in the budget so the
 * settings UI can drive them and they survive process death.
 */
class MovementGate(
    private val budget: MovementGateBudget,
    initialAreaGate: MoneoAreaGate = MoneoAreaGate.DISABLED,
) {
    val enabled = budget.gateEnabled

    /**
     * Currently active area gate. Volatile because the runner thread reads
     * it every frame while the activity may swap it in once at startup
     * after MoneoModule is built.
     */
    @Volatile
    private var areaGate: MoneoAreaGate = initialAreaGate

    /** Replace the area gate. Activity uses this after Moneo wires up. */
    fun setAreaGate(value: MoneoAreaGate) {
        areaGate = value
    }

    /** Exposed so callers (HUD) can observe the current gate's decisions. */
    val areaGateDecisions: kotlinx.coroutines.flow.StateFlow<AreaGateDecision>
        get() = areaGate.lastDecision

    private var prevSnapshot: LeafGreenRam.Snapshot? = null
    private var prevKeys: Int = 0

    fun setEnabled(value: Boolean) {
        budget.setGateEnabled(value)
    }

    /**
     * Run once per frame on the emulator thread. Returns the (possibly masked)
     * key bitmask that should be passed to `mCore->setKeys`.
     */
    fun process(rawKeys: Int, current: LeafGreenRam.Snapshot): Int {
        val prev = prevSnapshot
        if (prev != null && (prevKeys and DIR_MASK) != 0
            && prev.mapBank == current.mapBank && prev.mapId == current.mapId
            && (prev.playerX != current.playerX || prev.playerY != current.playerY)) {
            budget.consumeOneTile()
        }

        // Step gate: clear all DPAD bits when the budget is exhausted.
        var masked = if (budget.gateEnabled.value
            && budget.budget.value <= 0
            && (rawKeys and DIR_MASK) != 0) {
            rawKeys and DIR_MASK.inv()
        } else {
            rawKeys
        }

        // Area gate: clear only the specific direction(s) that would step into
        // a not-yet-mature area. Layered on top of the step gate so the two
        // can both contribute (the more restrictive wins). Snapshot the
        // volatile reference once for thread-safety.
        val ag = areaGate
        val decision = ag.evaluate(masked, current)
        if (decision.shouldBlock && decision.blockedDirMask != 0) {
            masked = masked and decision.blockedDirMask.inv()
        }

        prevSnapshot = current
        prevKeys = masked
        return masked
    }

    companion object {
        const val DIR_MASK = GbaKey.RIGHT or GbaKey.LEFT or GbaKey.UP or GbaKey.DOWN
    }
}
