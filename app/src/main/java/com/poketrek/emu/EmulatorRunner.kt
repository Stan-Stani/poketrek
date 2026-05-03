package com.poketrek.emu

import android.graphics.Bitmap
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioTrack
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

private const val SAMPLE_RATE = 48000
/** Headroom for ~one full frame of stereo samples + slack. */
private const val AUDIO_BUFFER_BYTES = 4096

/**
 * Owns the [NativeEmulator], the framebuffer Bitmap, and the run loop thread.
 *
 * The Compose UI observes [frameTick] (increments each rendered frame) and
 * draws [bitmap]. Input is set via [setKeys].
 */
class EmulatorRunner(budget: MovementBudget) {
    private val native = NativeEmulator()
    val gate: MovementGate = MovementGate(budget)

    fun saveState(): ByteArray? = native.saveState()
    fun loadState(bytes: ByteArray): Boolean = native.loadState(bytes)

    /** Direct ByteBuffer the native side writes into; rewound before each copy. */
    private val frameBuf: ByteBuffer = ByteBuffer
        .allocateDirect(FRAMEBUFFER_BYTES)
        .order(ByteOrder.nativeOrder())

    /** Direct ByteBuffer for audio samples; reused each frame. */
    private val audioBuf: ByteBuffer = ByteBuffer
        .allocateDirect(AUDIO_BUFFER_BYTES)
        .order(ByteOrder.nativeOrder())

    private var audioTrack: AudioTrack? = null

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

    /** Identity (CRC32 + variant) of the currently-loaded ROM, or null when none. */
    private val _romIdentity = mutableStateOf<RomIdentity?>(null)
    val romIdentity: androidx.compose.runtime.State<RomIdentity?> = _romIdentity

    private val running = AtomicBoolean(false)
    private val keys = AtomicInteger(0)
    private var thread: Thread? = null

    fun loadRom(bytes: ByteArray): Boolean {
        stop()
        val ok = native.loadRom(bytes)
        if (!ok) {
            Log.e(TAG, "loadRom returned false")
            _romIdentity.value = null
            return false
        }
        _romIdentity.value = RomIdentity.of(bytes)
            .also { Log.i(TAG, "loaded ${it.variant.displayName} (${it.crc32Hex})") }
        native.initAudio(SAMPLE_RATE)
        startAudio()
        _romLoaded.value = true
        start()
        return true
    }

    private fun startAudio() {
        val minBuf = AudioTrack.getMinBufferSize(
            SAMPLE_RATE,
            AudioFormat.CHANNEL_OUT_STEREO,
            AudioFormat.ENCODING_PCM_16BIT,
        )
        // Double the minimum to absorb scheduling jitter without underrunning.
        val bufSize = (minBuf * 2).coerceAtLeast(AUDIO_BUFFER_BYTES)
        audioTrack = AudioTrack.Builder()
            .setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_GAME)
                    .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                    .build(),
            )
            .setAudioFormat(
                AudioFormat.Builder()
                    .setSampleRate(SAMPLE_RATE)
                    .setChannelMask(AudioFormat.CHANNEL_OUT_STEREO)
                    .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                    .build(),
            )
            .setBufferSizeInBytes(bufSize)
            .setTransferMode(AudioTrack.MODE_STREAM)
            .build()
            .also { it.play() }
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
        audioTrack?.let {
            it.stop()
            it.release()
        }
        audioTrack = null
        if (_romLoaded.value) {
            native.destroy()
            _romLoaded.value = false
            _romIdentity.value = null
        }
    }

    private fun runLoop() {
        var nextFrameAt = System.nanoTime()
        while (running.get()) {
            val rawKeys = keys.get()
            val snapshot = LeafGreenRam.read(native)
            // For ROM variants we haven't calibrated, skip gating entirely —
            // LeafGreenRam reads at addresses that won't be valid on those
            // builds, and the budget would burn out from random RAM diffs.
            val gated = if (_romIdentity.value?.variant?.gatingSupported == false) {
                rawKeys
            } else {
                gate.process(rawKeys, snapshot)
            }
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
            audioTrack?.let { track ->
                val frames = native.pollAudio(audioBuf)
                if (frames > 0) {
                    val bytes = frames * 4  // 2 channels * 2 bytes
                    audioBuf.position(0).limit(bytes)
                    track.write(audioBuf, bytes, AudioTrack.WRITE_NON_BLOCKING)
                    audioBuf.clear()
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
