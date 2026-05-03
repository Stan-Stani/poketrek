package com.poketrek.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.FilterQuality
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import com.poketrek.emu.EmulatorRunner
import com.poketrek.step.MovementBudget

/**
 * Full-screen emulator: framebuffer letterboxed across the entire window,
 * with semi-transparent controls floating on top. This frees the game to
 * render at maximum size, with the on-screen controls overlaid in the
 * letterbox margins where they don't obscure gameplay.
 */
@Composable
fun EmulatorScreen(
    runner: EmulatorRunner,
    budget: MovementBudget,
    onDebugAddSteps: (Int) -> Unit,
    onSaveState: () -> Unit,
    onLoadState: () -> Unit,
    canLoadState: () -> Boolean,
    modifier: Modifier = Modifier,
) {
    val tick by runner.frameTick
    val ramSnapshot by runner.ramSnapshot
    val controlState = rememberControlState()

    Box(modifier = modifier.fillMaxSize().background(Color.Black)) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            @Suppress("UNUSED_VARIABLE") val t = tick
            drawFramebuffer(runner)
        }

        HudOverlay(
            budget = budget,
            gate = runner.gate,
            ramSnapshot = ramSnapshot,
            onDebugAddSteps = onDebugAddSteps,
            onSaveState = onSaveState,
            onLoadState = onLoadState,
            canLoadState = canLoadState,
            modifier = Modifier
                .align(Alignment.TopStart)
                .padding(8.dp),
        )

        StartSelectChips(
            state = controlState,
            onKeysChanged = runner::setKeys,
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(8.dp),
        )

        DPadCluster(
            state = controlState,
            onKeysChanged = runner::setKeys,
            modifier = Modifier
                .align(Alignment.BottomStart)
                .padding(start = 16.dp, bottom = 16.dp),
        )

        ActionCluster(
            state = controlState,
            onKeysChanged = runner::setKeys,
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .padding(end = 16.dp, bottom = 16.dp),
        )
    }
}

private fun DrawScope.drawFramebuffer(runner: EmulatorRunner) {
    val bmp = runner.bitmap
    val srcW = bmp.width
    val srcH = bmp.height
    val canvasW = size.width.toInt()
    val canvasH = size.height.toInt()
    val scale = minOf(canvasW.toFloat() / srcW, canvasH.toFloat() / srcH)
    val drawW = (srcW * scale).toInt()
    val drawH = (srcH * scale).toInt()
    val offsetX = (canvasW - drawW) / 2
    val offsetY = (canvasH - drawH) / 2
    val snapshot = synchronized(bmp) { bmp.asImageBitmap() }
    drawImage(
        image = snapshot,
        srcOffset = IntOffset.Zero,
        srcSize = IntSize(srcW, srcH),
        dstOffset = IntOffset(offsetX, offsetY),
        dstSize = IntSize(drawW, drawH),
        filterQuality = FilterQuality.None,
    )
}
