package com.poketrek.emu

import com.poketrek.step.MovementBudget

/**
 * The actual step-gating logic. Sits between the emulator's frame loop and
 * mGBA's setKeys: every frame, [process] (a) detects player tile transitions
 * by diffing the LeafGreen RAM snapshot vs the previous frame and consumes
 * one tile from the [MovementBudget] when one occurs, and (b) masks the
 * direction bits out of the key bitmask when the gate is enabled and the
 * budget is exhausted.
 *
 * The decrement rule mirrors the plan: only count a step if (X or Y changed)
 * AND (map ID unchanged — otherwise we're warping through a door) AND
 * (a direction was held last frame — so cutscenes/scripted movement and
 * ledge hops/ice tiles don't get charged).
 *
 * The gate-enabled flag and current budget live in [MovementBudget] so the
 * settings UI can drive them and they survive process death.
 */
class MovementGate(private val budget: MovementBudget) {
    val enabled = budget.gateEnabled

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

        val masked = if (budget.gateEnabled.value
            && budget.budget.value <= 0
            && (rawKeys and DIR_MASK) != 0) {
            rawKeys and DIR_MASK.inv()
        } else {
            rawKeys
        }

        prevSnapshot = current
        prevKeys = masked
        return masked
    }

    companion object {
        private const val DIR_MASK = GbaKey.RIGHT or GbaKey.LEFT or GbaKey.UP or GbaKey.DOWN
    }
}
