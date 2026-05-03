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
    onDebugAddSteps: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val tiles by budget.budget.collectAsState()
    val ratio by budget.tilesPerStep.collectAsState()

    Row(
        modifier = modifier
            .background(Color(0xCC000000), shape = RoundedCornerShape(12.dp))
            .padding(horizontal = 12.dp, vertical = 6.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
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
}
