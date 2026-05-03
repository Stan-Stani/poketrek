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
import androidx.compose.foundation.shape.RoundedCornerShape
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
import com.poketrek.step.MAX_RATIO
import com.poketrek.step.MIN_RATIO
import com.poketrek.step.MovementBudget

/**
 * Compact, always-visible HUD: just the tile count + a button that opens the
 * settings sheet. Sits in the corner of the framebuffer letterbox so it
 * doesn't overlap gameplay.
 */
@Composable
fun HudBadge(
    budget: MovementBudget,
    onOpenSettings: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val tiles by budget.budget.collectAsState()
    val gateOn by budget.gateEnabled.collectAsState()
    Row(
        modifier = modifier
            .background(Color(0xCC000000), shape = RoundedCornerShape(10.dp))
            .padding(horizontal = 8.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text(
            text = if (gateOn) "TILES $tiles" else "TILES $tiles (free)",
            color = if (gateOn && tiles == 0) Color(0xFFEF4444) else Color.White,
            fontFamily = FontFamily.Monospace,
            fontWeight = FontWeight.Bold,
            fontSize = 13.sp,
        )
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
    onDebugAddSteps: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .background(Color(0xCC000000), shape = RoundedCornerShape(8.dp))
            .padding(horizontal = 8.dp, vertical = 4.dp),
        verticalArrangement = Arrangement.spacedBy(2.dp),
    ) {
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
    onSaveState: () -> Unit,
    onLoadState: () -> Unit,
    canLoadState: Boolean,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val tiles by budget.budget.collectAsState()
    val ratio by budget.tilesPerStep.collectAsState()
    val gateOn by budget.gateEnabled.collectAsState()
    val debugOn by budget.debugHudVisible.collectAsState()
    var ratioDraft by remember(ratio) { mutableStateOf(ratio.toFloat()) }

    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = sheetState) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 24.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("PokéTrek settings", fontWeight = FontWeight.Bold, fontSize = 18.sp)

            ToggleRow(
                label = "Step gate",
                sublabel = if (gateOn) "Movement requires real steps" else "Free walking",
                checked = gateOn,
                onCheckedChange = { gate.setEnabled(it) },
            )

            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(
                    "1 real step = ${ratioDraft.toInt()} tiles",
                    fontFamily = FontFamily.Monospace,
                    fontSize = 14.sp,
                )
                Slider(
                    value = ratioDraft,
                    onValueChange = { ratioDraft = it },
                    onValueChangeFinished = { budget.setTilesPerStep(ratioDraft.toInt()) },
                    valueRange = MIN_RATIO.toFloat()..MAX_RATIO.toFloat(),
                    steps = (MAX_RATIO - MIN_RATIO) - 1,
                )
            }

            Text(
                "Current budget: $tiles tiles",
                color = Color(0xFF6B7280),
                fontFamily = FontFamily.Monospace,
                fontSize = 12.sp,
            )

            ToggleRow(
                label = "Debug overlay",
                sublabel = "Shows RAM probe + fake-step button",
                checked = debugOn,
                onCheckedChange = { budget.setDebugHudVisible(it) },
            )

            Spacer(Modifier.height(4.dp))
            Text("Save state", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Button(onClick = { onSaveState(); onDismiss() }) { Text("Save") }
                Button(onClick = { onLoadState(); onDismiss() }, enabled = canLoadState) {
                    Text("Load")
                }
            }
            Spacer(Modifier.height(8.dp))
        }
    }
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
