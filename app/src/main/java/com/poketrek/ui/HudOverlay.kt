package com.poketrek.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.poketrek.emu.MovementGate
import com.poketrek.step.MovementBudget

/**
 * Discrete ratio steps the slider snaps through. Index 0 is the hardest
 * (most real steps per tile); the last index is the easiest. The middle
 * stop is realistic 1:1.
 */
private val RATIO_TABLE: List<Pair<Int, Int>> = listOf(
    1 to 8, 1 to 6, 1 to 4, 1 to 3, 1 to 2,
    1 to 1,
    2 to 1, 3 to 1, 4 to 1, 6 to 1, 8 to 1, 12 to 1, 16 to 1,
)

private fun ratioIndexFor(num: Int, den: Int): Int {
    val idx = RATIO_TABLE.indexOfFirst { it.first == num && it.second == den }
    return if (idx >= 0) idx else RATIO_TABLE.indexOfFirst { it.first == 1 && it.second == 1 }
}

private fun describeRatio(num: Int, den: Int): String = when {
    num == 1 && den == 1 -> "1 step = 1 tile (realistic)"
    num >= den -> {
        val tiles = num / den
        "1 step = $tiles tile${if (tiles != 1) "s" else ""}"
    }
    else -> {
        val steps = den / num
        "$steps steps = 1 tile"
    }
}

/**
 * Compact, always-visible HUD: just the tile count + a button that opens the
 * settings sheet. Sits in the corner of the framebuffer letterbox so it
 * doesn't overlap gameplay.
 */
@Composable
fun HudBadge(
    budget: MovementBudget,
    romIdentity: com.poketrek.emu.RomIdentity?,
    onOpenSettings: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val tiles by budget.budget.collectAsState()
    val gateOn by budget.gateEnabled.collectAsState()
    val warn = romIdentity != null && !romIdentity.variant.gatingSupported
    Row(
        modifier = modifier
            .background(Color(0xCC000000), shape = RoundedCornerShape(10.dp))
            .padding(horizontal = 8.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Column {
            Text(
                text = if (gateOn) "TILES $tiles" else "TILES $tiles (free)",
                color = if (gateOn && tiles == 0) Color(0xFFEF4444) else Color.White,
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.Bold,
                fontSize = 13.sp,
            )
            if (warn) {
                Text(
                    text = "⚠ ${romIdentity!!.variant.displayName} — gating off",
                    color = Color(0xFFFBBF24),
                    fontFamily = FontFamily.Monospace,
                    fontSize = 9.sp,
                )
            }
        }
        Button(
            onClick = onOpenSettings,
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF374151)),
            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 0.dp),
        ) {
            Text("☰", color = Color.White, fontSize = 13.sp)
        }
    }
}

/**
 * Lightweight read-only debug overlay: shows the RAM probe snapshot. Only
 * rendered when the user has enabled the debug HUD in settings. Designed to
 * sit somewhere unobtrusive (top-center letterbox).
 */
@Composable
fun DebugOverlay(
    snapshot: com.poketrek.emu.LeafGreenRam.Snapshot?,
    romIdentity: com.poketrek.emu.RomIdentity?,
    onDebugAddSteps: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .background(Color(0xCC000000), shape = RoundedCornerShape(8.dp))
            .padding(horizontal = 8.dp, vertical = 4.dp),
        verticalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        if (romIdentity != null) {
            Text(
                text = "ROM: ${romIdentity.variant.displayName} ${romIdentity.crc32Hex}",
                color = Color(0xFF9CA3AF),
                fontFamily = FontFamily.Monospace,
                fontSize = 10.sp,
            )
        }
        if (snapshot != null) {
            Text(
                text = formatSnapshot(snapshot),
                color = Color(0xFF9CA3AF),
                fontFamily = FontFamily.Monospace,
                fontSize = 10.sp,
            )
        }
        Button(
            onClick = { onDebugAddSteps(10) },
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF6366F1)),
            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 0.dp),
        ) {
            Text("+10 fake steps", color = Color.White, fontSize = 11.sp)
        }
    }
}

/**
 * Modal bottom sheet with all user-tweakable knobs. Hidden by default; opened
 * from the HUD badge.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsSheet(
    budget: MovementBudget,
    gate: MovementGate,
    onDismiss: () -> Unit,
    onPickRom: () -> Unit,
    getSaveSlots: () -> List<com.poketrek.emu.SaveStateStore.Slot>,
    onSaveSlot: (Int) -> Boolean,
    onLoadSlot: (Int) -> Boolean,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val tiles by budget.budget.collectAsState()
    val ratioNum by budget.tilesPerStepNum.collectAsState()
    val ratioDen by budget.tilesPerStepDen.collectAsState()
    val gateOn by budget.gateEnabled.collectAsState()
    val debugOn by budget.debugHudVisible.collectAsState()
    val hapticOn by budget.hapticOnStep.collectAsState()
    val currentIndex = ratioIndexFor(ratioNum, ratioDen)
    var ratioDraft by remember(currentIndex) { mutableStateOf(currentIndex.toFloat()) }
    val draftIndex = ratioDraft.toInt().coerceIn(0, RATIO_TABLE.lastIndex)
    val (draftNum, draftDen) = RATIO_TABLE[draftIndex]

    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = sheetState) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text("PokéTrek settings", fontWeight = FontWeight.Bold, fontSize = 18.sp)
                Button(
                    onClick = { onPickRom(); onDismiss() },
                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 0.dp),
                ) {
                    Text("Change ROM…", fontSize = 12.sp)
                }
            }

            ToggleRow(
                label = "Step gate",
                sublabel = if (gateOn) "Movement requires real steps" else "Free walking",
                checked = gateOn,
                onCheckedChange = { gate.setEnabled(it) },
            )

            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(
                    describeRatio(draftNum, draftDen),
                    fontFamily = FontFamily.Monospace,
                    fontSize = 14.sp,
                )
                Slider(
                    value = ratioDraft,
                    onValueChange = { ratioDraft = it },
                    onValueChangeFinished = {
                        val (n, d) = RATIO_TABLE[draftIndex]
                        budget.setRatio(n, d)
                    },
                    valueRange = 0f..(RATIO_TABLE.lastIndex).toFloat(),
                    steps = RATIO_TABLE.size - 2,
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Text(
                        "8 steps / tile",
                        color = Color(0xFF6B7280),
                        fontSize = 11.sp,
                    )
                    Text(
                        "16 tiles / step",
                        color = Color(0xFF6B7280),
                        fontSize = 11.sp,
                    )
                }
            }

            Text(
                "Current budget: $tiles tiles",
                color = Color(0xFF6B7280),
                fontFamily = FontFamily.Monospace,
                fontSize = 12.sp,
            )

            ToggleRow(
                label = "Vibrate on step credit",
                sublabel = "Brief pulse when a real step adds to your tile budget",
                checked = hapticOn,
                onCheckedChange = { budget.setHapticOnStep(it) },
            )

            ToggleRow(
                label = "Debug overlay",
                sublabel = "Shows RAM probe + fake-step button",
                checked = debugOn,
                onCheckedChange = { budget.setDebugHudVisible(it) },
            )

            Spacer(Modifier.height(4.dp))
            Text("Save states", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
            var slotsVersion by remember { mutableStateOf(0) }
            val slots = remember(slotsVersion) { getSaveSlots() }
            slots.forEach { slot ->
                SlotRow(
                    slot = slot,
                    onSave = {
                        if (onSaveSlot(slot.index)) slotsVersion++
                    },
                    onLoad = {
                        if (onLoadSlot(slot.index)) onDismiss()
                    },
                )
            }
            Spacer(Modifier.height(8.dp))
        }
    }
}

@Composable
private fun SlotRow(
    slot: com.poketrek.emu.SaveStateStore.Slot,
    onSave: () -> Unit,
    onLoad: () -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Column(Modifier.weight(1f)) {
            Text("Slot ${slot.index}", fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
            Text(
                if (slot.isEmpty) "Empty" else relativeTime(slot.savedAt!!),
                color = Color(0xFF6B7280),
                fontSize = 11.sp,
            )
        }
        Button(onClick = onSave, contentPadding = PaddingValues(horizontal = 12.dp, vertical = 0.dp)) {
            Text("Save", fontSize = 12.sp)
        }
        Button(
            onClick = onLoad,
            enabled = !slot.isEmpty,
            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 0.dp),
        ) {
            Text("Load", fontSize = 12.sp)
        }
    }
}

private fun relativeTime(epochMs: Long): String {
    val cs = android.text.format.DateUtils.getRelativeTimeSpanString(
        epochMs,
        System.currentTimeMillis(),
        android.text.format.DateUtils.MINUTE_IN_MILLIS,
        android.text.format.DateUtils.FORMAT_ABBREV_RELATIVE,
    )
    return cs?.toString() ?: "unknown"
}

@Composable
private fun ToggleRow(
    label: String,
    sublabel: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(label, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
            Text(sublabel, color = Color(0xFF6B7280), fontSize = 12.sp)
        }
        Spacer(Modifier.width(8.dp))
        Switch(
            checked = checked,
            onCheckedChange = onCheckedChange,
            colors = SwitchDefaults.colors(),
        )
    }
}

private fun formatSnapshot(s: com.poketrek.emu.LeafGreenRam.Snapshot): String {
    fun hex(v: Int, width: Int) = "0x" + v.toUInt().toString(16).padStart(width, '0').uppercase()
    return "X:${s.playerX} Y:${s.playerY} bank:${s.mapBank}/${s.mapId} mov:${s.movingStatus} sb1=${hex(s.saveBlockPtr, 8)}"
}
