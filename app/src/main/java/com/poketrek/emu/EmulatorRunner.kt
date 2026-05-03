package com.poketrek.emu

import android.graphics.Bitmap
import android.util.Log
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.poketrek.step.MovementBudget
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger
import kotlin.concurrent.thread

private const val TAG = "EmulatorRunner"

/** GBA framebuffer is 240x160 RGBA8888. */
private const val GBA_W = 240
private const val GBA_H = 160
private const val FRAMEBUFFER_BYTES = GBA_W * GBA_H * 4

/** Targeted GBA frame period — actual mGBA rate is 59.7275 Hz. */
private const val FRAME_PERIOD_NS = 16_750_419L

/**
 * Owns the [NativeEmulator], the framebuffer Bitmap, and the run loop thread.
 *
 * The Compose UI observes [frameTick] (increments each rendered frame) and
 * draws [bitmap]. Input is set via [setKeys].
 */
class EmulatorRunner(budget: MovementBudget) {
    private val native = NativeEmulator()
    val gate: MovementGate = MovementGate(budget)

    /** Direct ByteBuffer the native side writes into; rewound before each copy. */
    private val frameBuf: ByteBuffer = ByteBuffer
        .allocateDirect(FRAMEBUFFER_BYTES)
        .order(ByteOrder.nativeOrder())

    /** UI bitmap; pixels mutated each frame via copyPixelsFromBuffer. */
    val bitmap: Bitmap = Bitmap.createBitmap(GBA_W, GBA_H, Bitmap.Config.ARGB_8888)

    /** Compose state tick: read by the screen Composable to force recomposition. */
    private val _frameTick = mutableIntStateOf(0)
    val frameTick: androidx.compose.runtime.State<Int> = _frameTick

    /** Current ROM-loaded state for the UI. */
    private val _romLoaded = mutableStateOf(false)
    val romLoaded: androidx.compose.runtime.State<Boolean> = _romLoaded

    /** Latest LeafGreen RAM snapshot, updated every ~30 frames (~0.5s). */
    private val _ramSnapshot = mutableStateOf<com.poketrek.emu.LeafGreenRam.Snapshot?>(null)
    val ramSnapshot: androidx.compose.runtime.State<com.poketrek.emu.LeafGreenRam.Snapshot?> = _ramSnapshot

    private val running = AtomicBoolean(false)
    private val keys = AtomicInteger(0)
    private var thread: Thread? = null

    fun loadRom(bytes: ByteArray): Boolean {
        stop()
        val ok = native.loadRom(bytes)
        if (!ok) {
            Log.e(TAG, "loadRom returned false")
            return false
        }
        _romLoaded.value = true
        start()
        return true
    }

    fun setKeys(mask: Int) {
        keys.set(mask)
    }

    private fun start() {
        if (running.getAndSet(true)) return
        thread = thread(name = "emulator-runner", isDaemon = true) { runLoop() }
    }

    fun stop() {
        running.set(false)
        thread?.join(500)
        thread = null
        if (_romLoaded.value) {
            native.destroy()
            _romLoaded.value = false
        }
    }

    private fun runLoop() {
        var nextFrameAt = System.nanoTime()
        while (running.get()) {
            val rawKeys = keys.get()
            val snapshot = LeafGreenRam.read(native)
            val gated = gate.process(rawKeys, snapshot)
            native.setKeys(gated)
            native.runFrame()
            if (native.writeFramebuffer(frameBuf)) {
                frameBuf.rewind()
                synchronized(bitmap) {
                    bitmap.copyPixelsFromBuffer(frameBuf)
                }
                val nextTick = _frameTick.intValue + 1
                _frameTick.intValue = nextTick
                if (nextTick % 30 == 0) {
                    _ramSnapshot.value = snapshot
                }
            }
            nextFrameAt += FRAME_PERIOD_NS
            val sleepNs = nextFrameAt - System.nanoTime()
            if (sleepNs > 0) {
                try {
                    Thread.sleep(sleepNs / 1_000_000L, (sleepNs % 1_000_000L).toInt())
                } catch (_: InterruptedException) {
                    return
                }
            } else if (sleepNs < -FRAME_PERIOD_NS * 4) {
                // Fell behind by 4+ frames; resync rather than spin trying to catch up.
                nextFrameAt = System.nanoTime()
            }
        }
    }
}
