package com.poketrek.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
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
import com.poketrek.moneo.MoneoModule
import com.poketrek.moneo.gate.MoneoSoftGate
import com.poketrek.moneo.ui.MoneoHud
import com.poketrek.moneo.ui.MoneoOverlay
import com.poketrek.step.MovementBudget

/**
 * Full-screen emulator: framebuffer letterboxed across the entire window,
 * with semi-transparent controls floating on top. The HUD is just a tiny
 * badge + a settings sheet so it doesn't cover the game.
 */
@Composable
fun EmulatorScreen(
    runner: EmulatorRunner,
    budget: MovementBudget,
    moneo: MoneoModule,
    moneoGate: MoneoSoftGate,
    onDebugAddSteps: (Int) -> Unit,
    onPickRom: () -> Unit,
    getSaveSlots: () -> List<com.poketrek.emu.SaveStateStore.Slot>,
    onSaveSlot: (Int) -> Boolean,
    onLoadSlot: (Int) -> Boolean,
    getRomLibrary: () -> List<com.poketrek.emu.RomCache.Slot> = { emptyList() },
    currentRomCrc32: () -> Long? = { null },
    onLoadCachedRom: (Long) -> Boolean = { false },
    onRemoveCachedRom: (Long) -> Unit = {},
    modifier: Modifier = Modifier,
) {
    val tick by runner.frameTick
    val ramSnapshot by runner.ramSnapshot
    val romIdentity by runner.romIdentity
    val debugOn by budget.debugHudVisible.collectAsState()
    val pendingBaseline by runner.calibrationBaseline
    val calibrationStatus by runner.calibrationStatus
    val hasCalibration by runner.hasCalibration
    val controlState = rememberControlState()
    var settingsOpen by remember { mutableStateOf(false) }
    var moneoOpen by remember { mutableStateOf(false) }

    Box(modifier = modifier.fillMaxSize().background(Color.Black)) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            @Suppress("UNUSED_VARIABLE") val t = tick
            drawFramebuffer(runner)
        }

        HudBadge(
            budget = budget,
            romIdentity = romIdentity,
            hasCalibration = hasCalibration,
            onOpenSettings = { settingsOpen = true },
            modifier = Modifier
                .align(Alignment.TopStart)
                .padding(8.dp),
        )

        MoneoHud(
            gate = moneoGate,
            onOpenMoneo = { moneoOpen = true },
            modifier = Modifier
                .align(Alignment.TopStart)
                .padding(start = 8.dp, top = 56.dp),
        )

        AreaGateLockChip(
            gate = runner.gate,
            moneo = moneo,
            modifier = Modifier
                .align(Alignment.TopStart)
                .padding(start = 8.dp, top = 96.dp),
        )

        if (debugOn) {
            DebugOverlay(
                snapshot = ramSnapshot,
                romIdentity = romIdentity,
                onDebugAddSteps = onDebugAddSteps,
                modifier = Modifier
                    .align(Alignment.TopCenter)
                    .padding(top = 8.dp),
            )
        }

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

        if (pendingBaseline != null && !settingsOpen) {
            CalibrationPendingChip(
                onCapture = { runner.finishCalibration() },
                onShowSettings = { settingsOpen = true },
                modifier = Modifier
                    .align(Alignment.TopCenter)
                    .padding(top = 8.dp),
            )
        }

        if (settingsOpen) {
            SettingsSheet(
                budget = budget,
                gate = runner.gate,
                romIdentity = romIdentity,
                onDismiss = { settingsOpen = false },
                onPickRom = onPickRom,
                getSaveSlots = getSaveSlots,
                onSaveSlot = onSaveSlot,
                onLoadSlot = onLoadSlot,
                onBuyRareCandy = runner::buyRareCandy,
                hasCalibration = hasCalibration,
                hasPendingBaseline = pendingBaseline != null,
                calibrationStatus = calibrationStatus,
                onBeginCalibration = runner::beginCalibration,
                onFinishCalibration = runner::finishCalibration,
                onCancelCalibration = runner::cancelCalibration,
                onClearCalibrationStatus = runner::clearCalibrationStatus,
                moneo = moneo,
                onOpenMoneo = { moneoOpen = true },
                getRomLibrary = getRomLibrary,
                currentRomCrc32 = currentRomCrc32,
                onLoadCachedRom = onLoadCachedRom,
                onRemoveCachedRom = onRemoveCachedRom,
            )
        }

        if (moneoOpen) {
            MoneoOverlay(
                module = moneo,
                onClose = { moneoOpen = false },
                modifier = Modifier.fillMaxSize(),
            )
        }
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
