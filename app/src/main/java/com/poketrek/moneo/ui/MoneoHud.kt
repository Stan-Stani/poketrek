package com.poketrek.moneo.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.poketrek.moneo.gate.MoneoSoftGate

/**
 * Compact "복습 N due / Review N due" badge. Only emits when the gate
 * publishes a non-null Badge; tap opens the Moneo overlay.
 */
@Composable
fun MoneoHud(
    gate: MoneoSoftGate,
    onOpenMoneo: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val badge by gate.badge.collectAsState()
    val b = badge ?: return
    Row(
        modifier = modifier
            .background(Color(0xCC1E3A8A), shape = RoundedCornerShape(10.dp))
            .padding(horizontal = 8.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Column {
            Text(
                "복습 ${b.dueCount}",
                color = Color.White,
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.Bold,
                fontSize = 13.sp,
            )
            Text(
                "Review due",
                color = Color(0xFFBFDBFE),
                fontSize = 9.sp,
            )
        }
        Button(
            onClick = onOpenMoneo,
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1D4ED8)),
            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 0.dp),
        ) {
            Text("Study", color = Color.White, fontSize = 11.sp)
        }
    }
}
