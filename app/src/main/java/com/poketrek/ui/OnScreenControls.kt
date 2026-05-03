package com.poketrek.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.PointerEventType
import androidx.compose.ui.input.pointer.PointerId
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.poketrek.emu.GbaKey

private val ButtonBg = Color(0x99374151)
private val DPadBg = Color(0xCC1F2937)

/**
 * Container that handles the shared state across all on-screen controls.
 * Each child reports its bit + pressed-state via [onUpdate]; this composable
 * coalesces them into one bitmask that's reported on every change.
 */
@Composable
fun rememberControlState(): ControlState = remember { ControlState() }

class ControlState {
    private val _keys = mutableIntStateOf(0)
    val keys: Int get() = _keys.intValue

    fun update(bit: Int, down: Boolean): Int {
        val next = if (down) _keys.intValue or bit else _keys.intValue and bit.inv()
        _keys.intValue = next
        return next
    }
}

@Composable
fun StartSelectChips(
    state: ControlState,
    onKeysChanged: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        PillButton("SELECT", GbaKey.SELECT, state, onKeysChanged)
        PillButton("START", GbaKey.START, state, onKeysChanged)
    }
}

@Composable
fun DPadCluster(
    state: ControlState,
    onKeysChanged: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val cellSize = 56.dp
    Box(
        modifier = modifier
            .size(cellSize * 3)
            .dpadSlide(cellSize, state, onKeysChanged),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            DPadButton("▲")
            Row {
                DPadButton("◀")
                Spacer(Modifier.size(cellSize))
                DPadButton("▶")
            }
            DPadButton("▼")
        }
    }
}

@Composable
fun ActionCluster(
    state: ControlState,
    onKeysChanged: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier,
        horizontalAlignment = Alignment.End,
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            ShoulderButton("L", GbaKey.L, state, onKeysChanged)
            ShoulderButton("R", GbaKey.R, state, onKeysChanged)
        }
        Row(horizontalArrangement = Arrangement.spacedBy(20.dp)) {
            RoundButton("B", GbaKey.B, Color(0xCCE63946), state, onKeysChanged)
            RoundButton("A", GbaKey.A, Color(0xCC06A77D), state, onKeysChanged)
        }
    }
}

@Composable
private fun DPadButton(glyph: String) {
    Box(
        modifier = Modifier
            .size(56.dp)
            .background(DPadBg, shape = RoundedCornerShape(6.dp)),
        contentAlignment = Alignment.Center,
    ) {
        Text(glyph, color = Color.White, fontSize = 24.sp)
    }
}

@Composable
private fun RoundButton(
    label: String,
    bit: Int,
    color: Color,
    state: ControlState,
    onKeysChanged: (Int) -> Unit,
) {
    Box(
        modifier = Modifier
            .size(72.dp)
            .background(color, shape = CircleShape)
            .pressBit(bit, state, onKeysChanged),
        contentAlignment = Alignment.Center,
    ) {
        Text(label, color = Color.White, fontSize = 24.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun PillButton(
    label: String,
    bit: Int,
    state: ControlState,
    onKeysChanged: (Int) -> Unit,
) {
    Box(
        modifier = Modifier
            .width(80.dp)
            .height(28.dp)
            .background(ButtonBg, shape = RoundedCornerShape(14.dp))
            .pressBit(bit, state, onKeysChanged),
        contentAlignment = Alignment.Center,
    ) {
        Text(label, color = Color.White, fontSize = 11.sp, textAlign = TextAlign.Center)
    }
}

@Composable
private fun ShoulderButton(
    label: String,
    bit: Int,
    state: ControlState,
    onKeysChanged: (Int) -> Unit,
) {
    Box(
        modifier = Modifier
            .size(width = 60.dp, height = 30.dp)
            .background(ButtonBg, shape = RoundedCornerShape(6.dp))
            .pressBit(bit, state, onKeysChanged),
        contentAlignment = Alignment.Center,
    ) {
        Text(label, color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Bold)
    }
}

private fun Modifier.pressBit(
    bit: Int,
    state: ControlState,
    onKeysChanged: (Int) -> Unit,
): Modifier = pointerInput(bit) {
    awaitPointerEventScope {
        var pressed = false
        while (true) {
            val event = awaitPointerEvent()
            val anyDown = event.changes.any { it.pressed }
            if (anyDown && !pressed) {
                pressed = true
                onKeysChanged(state.update(bit, true))
            } else if (!anyDown && pressed) {
                pressed = false
                onKeysChanged(state.update(bit, false))
            }
            if (event.type == PointerEventType.Release && !anyDown && pressed) {
                pressed = false
                onKeysChanged(state.update(bit, false))
            }
        }
    }
}

/**
 * Whole-cluster touch handler so a finger can slide between directions without
 * lifting. The cluster is laid out as a 3×3 grid of [cellSize] cells; each
 * active pointer maps to the bit of whichever cell it currently sits in
 * (center cell and out-of-bounds map to nothing). The union of every active
 * pointer's bit becomes the held d-pad mask.
 */
private fun Modifier.dpadSlide(
    cellSize: Dp,
    state: ControlState,
    onKeysChanged: (Int) -> Unit,
): Modifier = pointerInput(Unit) {
    val cellPx = cellSize.toPx()
    val pointerBits = mutableMapOf<PointerId, Int>()
    var ownedBits = 0

    fun bitAt(x: Float, y: Float): Int {
        if (x < 0f || y < 0f) return 0
        val col = (x / cellPx).toInt()
        val row = (y / cellPx).toInt()
        return when {
            col == 1 && row == 0 -> GbaKey.UP
            col == 0 && row == 1 -> GbaKey.LEFT
            col == 2 && row == 1 -> GbaKey.RIGHT
            col == 1 && row == 2 -> GbaKey.DOWN
            else -> 0
        }
    }

    awaitPointerEventScope {
        while (true) {
            val event = awaitPointerEvent()
            for (change in event.changes) {
                if (change.pressed) {
                    pointerBits[change.id] = bitAt(change.position.x, change.position.y)
                } else {
                    pointerBits.remove(change.id)
                }
            }
            val newBits = pointerBits.values.fold(0) { acc, b -> acc or b }
            if (newBits != ownedBits) {
                val toPress = newBits and ownedBits.inv()
                val toRelease = ownedBits and newBits.inv()
                var keys = state.keys
                if (toPress != 0) keys = state.update(toPress, true)
                if (toRelease != 0) keys = state.update(toRelease, false)
                ownedBits = newBits
                onKeysChanged(keys)
            }
        }
    }
}
