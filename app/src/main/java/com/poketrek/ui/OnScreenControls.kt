package com.poketrek.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.PointerEventType
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.poketrek.emu.GbaKey

/**
 * On-screen controls. Reports the current pressed-key bitmask to [onKeysChanged]
 * whenever any button changes state. Supports multi-touch correctly: each
 * pointer holds the bit for the button it touched down on until it lifts.
 */
@Composable
fun OnScreenControls(
    onKeysChanged: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    var keys by remember { mutableIntStateOf(0) }

    fun update(bit: Int, down: Boolean) {
        val next = if (down) keys or bit else keys and bit.inv()
        if (next != keys) {
            keys = next
            onKeysChanged(next)
        }
    }

    Row(
        modifier = modifier.padding(12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        // D-pad (left)
        DPad(onChange = ::update, modifier = Modifier.size(160.dp))

        Spacer(Modifier.weight(1f))

        // Start / Select (center column)
        Column(
            verticalArrangement = Arrangement.spacedBy(8.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            PillButton(label = "SELECT", bit = GbaKey.SELECT, onChange = ::update)
            PillButton(label = "START", bit = GbaKey.START, onChange = ::update)
        }

        Spacer(Modifier.weight(1f))

        // A / B / L / R (right)
        Column(
            verticalArrangement = Arrangement.spacedBy(8.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                ShoulderButton(label = "L", bit = GbaKey.L, onChange = ::update)
                ShoulderButton(label = "R", bit = GbaKey.R, onChange = ::update)
            }
            Row(horizontalArrangement = Arrangement.spacedBy(20.dp)) {
                RoundButton(label = "B", bit = GbaKey.B, color = Color(0xFFE63946), onChange = ::update)
                RoundButton(label = "A", bit = GbaKey.A, color = Color(0xFF06A77D), onChange = ::update)
            }
        }
    }
}

@Composable
private fun DPad(
    onChange: (bit: Int, down: Boolean) -> Unit,
    modifier: Modifier = Modifier,
) {
    Box(modifier = modifier, contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            DPadButton("▲", GbaKey.UP, onChange)
            Row {
                DPadButton("◀", GbaKey.LEFT, onChange)
                Spacer(Modifier.size(48.dp))
                DPadButton("▶", GbaKey.RIGHT, onChange)
            }
            DPadButton("▼", GbaKey.DOWN, onChange)
        }
    }
}

@Composable
private fun DPadButton(
    glyph: String,
    bit: Int,
    onChange: (bit: Int, down: Boolean) -> Unit,
) {
    Box(
        modifier = Modifier
            .size(48.dp)
            .background(Color(0xFF374151), shape = RoundedCornerShape(4.dp))
            .pressBit(bit, onChange),
        contentAlignment = Alignment.Center,
    ) {
        Text(glyph, color = Color.White, fontSize = 22.sp)
    }
}

@Composable
private fun RoundButton(
    label: String,
    bit: Int,
    color: Color,
    onChange: (bit: Int, down: Boolean) -> Unit,
) {
    Box(
        modifier = Modifier
            .size(64.dp)
            .background(color, shape = CircleShape)
            .pressBit(bit, onChange),
        contentAlignment = Alignment.Center,
    ) {
        Text(label, color = Color.White, fontSize = 22.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun PillButton(
    label: String,
    bit: Int,
    onChange: (bit: Int, down: Boolean) -> Unit,
) {
    Box(
        modifier = Modifier
            .width(80.dp)
            .height(28.dp)
            .background(Color(0xFF6B7280), shape = RoundedCornerShape(14.dp))
            .pressBit(bit, onChange),
        contentAlignment = Alignment.Center,
    ) {
        Text(label, color = Color.White, fontSize = 11.sp, textAlign = TextAlign.Center)
    }
}

@Composable
private fun ShoulderButton(
    label: String,
    bit: Int,
    onChange: (bit: Int, down: Boolean) -> Unit,
) {
    Box(
        modifier = Modifier
            .size(width = 56.dp, height = 28.dp)
            .background(Color(0xFF4B5563), shape = RoundedCornerShape(6.dp))
            .pressBit(bit, onChange),
        contentAlignment = Alignment.Center,
    ) {
        Text(label, color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Bold)
    }
}

private fun Modifier.pressBit(
    bit: Int,
    onChange: (bit: Int, down: Boolean) -> Unit,
): Modifier = pointerInput(bit) {
    awaitPointerEventScope {
        var pressed = false
        while (true) {
            val event = awaitPointerEvent()
            val anyDown = event.changes.any { it.pressed }
            if (anyDown && !pressed) {
                pressed = true
                onChange(bit, true)
            } else if (!anyDown && pressed) {
                pressed = false
                onChange(bit, false)
            }
            if (event.type == PointerEventType.Release && !anyDown && pressed) {
                pressed = false
                onChange(bit, false)
            }
        }
    }
}
