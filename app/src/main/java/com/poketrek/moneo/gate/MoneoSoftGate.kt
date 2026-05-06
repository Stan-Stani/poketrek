package com.poketrek.moneo.gate

import com.poketrek.moneo.data.MoneoPrefs
import com.poketrek.moneo.data.MoneoRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.launch

/**
 * Soft gate: produces a UX nudge ([badge]) when Moneo is enabled and the
 * currently-selected target area has cards due. Does NOT touch emulator
 * input — that comes in Phase 4 once Korean RAM addresses are calibrated.
 */
class MoneoSoftGate(
    private val repository: MoneoRepository,
    private val prefs: MoneoPrefs,
) {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    data class Badge(val areaId: String, val dueCount: Int)

    private val _badge = MutableStateFlow<Badge?>(null)
    val badge: StateFlow<Badge?> = _badge.asStateFlow()

    init {
        scope.launch {
            combine(
                prefs.enabled,
                prefs.targetAreaId,
                repository.cards,
            ) { enabled, areaId, _ ->
                if (!enabled || areaId == null) return@combine null
                val due = repository.dueCountForArea(areaId)
                if (due > 0) Badge(areaId, due) else null
            }.collect { _badge.value = it }
        }
    }
}
