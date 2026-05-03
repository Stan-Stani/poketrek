package com.poketrek.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.poketrek.step.MovementBudget

@Composable
fun HudOverlay(
    budget: MovementBudget,
    ramSnapshot: com.poketrek.emu.LeafGreenRam.Snapshot?,
    onDebugAddSteps: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val tiles by budget.budget.collectAsState()
    val ratio by budget.tilesPerStep.collectAsState()

    androidx.compose.foundation.layout.Column(
        modifier = modifier
            .background(Color(0xCC000000), shape = RoundedCornerShape(12.dp))
            .padding(horizontal = 12.dp, vertical = 6.dp),
        verticalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(
                text = "TILES: $tiles",
                color = Color.White,
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.Bold,
                fontSize = 14.sp,
            )
            Text(
                text = "1 step = $ratio",
                color = Color(0xFFB0B0B0),
                fontFamily = FontFamily.Monospace,
                fontSize = 12.sp,
            )
            Button(
                onClick = { onDebugAddSteps(10) },
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF6366F1)),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 8.dp, vertical = 0.dp),
            ) {
                Text("+10 steps", color = Color.White, fontSize = 11.sp)
            }
        }
        if (ramSnapshot != null) {
            Text(
                text = formatSnapshot(ramSnapshot),
                color = Color(0xFF9CA3AF),
                fontFamily = FontFamily.Monospace,
                fontSize = 10.sp,
            )
        }
    }
}

private fun formatSnapshot(s: com.poketrek.emu.LeafGreenRam.Snapshot): String {
    fun hex(v: Int, width: Int) = "0x" + v.toUInt().toString(16).padStart(width, '0').uppercase()
    return "X:${s.playerX} Y:${s.playerY} bank:${s.mapBank}/${s.mapId} mov:${s.movingStatus} sb1=${hex(s.saveBlockPtr, 8)}"
}
