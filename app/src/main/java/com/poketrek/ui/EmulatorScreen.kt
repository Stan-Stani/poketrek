package com.poketrek.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.FilterQuality
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import com.poketrek.emu.EmulatorRunner

@Composable
fun EmulatorScreen(
    runner: EmulatorRunner,
    modifier: Modifier = Modifier,
) {
    val tick by runner.frameTick

    Column(modifier = modifier.fillMaxSize().background(Color.Black)) {
        // Framebuffer fills available vertical space; controls take a fixed slice.
        Canvas(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f),
        ) {
            @Suppress("UNUSED_VARIABLE") val t = tick
            drawFramebuffer(runner)
        }

        OnScreenControls(
            onKeysChanged = runner::setKeys,
            modifier = Modifier
                .fillMaxWidth()
                .height(220.dp),
        )
    }
}

private fun DrawScope.drawFramebuffer(runner: EmulatorRunner) {
    val bmp = runner.bitmap
    val srcW = bmp.width
    val srcH = bmp.height
    val canvasW = size.width.toInt()
    val canvasH = size.height.toInt()
    // Letterbox to preserve 240:160 (3:2) aspect.
    val scale = minOf(canvasW.toFloat() / srcW, canvasH.toFloat() / srcH)
    val drawW = (srcW * scale).toInt()
    val drawH = (srcH * scale).toInt()
    val offsetX = (canvasW - drawW) / 2
    val offsetY = (canvasH - drawH) / 2
    // Snapshot the bitmap under its lock so the runner thread doesn't tear pixels mid-draw.
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
