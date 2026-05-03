package com.poketrek.step

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.os.SystemClock
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.util.Log
import androidx.core.app.NotificationCompat
import com.poketrek.EmulatorActivity
import com.poketrek.R
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

private const val TAG = "StepCounterService"
private const val CHANNEL_ID = "poketrek_step_counter"
private const val NOTIFICATION_ID = 1001
private const val HAPTIC_PULSE_MS = 15L
/** Don't fire vibrations closer than this — the sensor sometimes batches bursts. */
private const val HAPTIC_MIN_GAP_MS = 120L

/**
 * Foreground service that owns the step-counter sensor registration so the
 * movement budget keeps accumulating while the app is backgrounded or the
 * screen is off. Required for the project's core use case: walk around with
 * the phone in your pocket, then play.
 *
 * Started by the Activity on first launch. Self-restarts on process death
 * via START_STICKY.
 */
class StepCounterService : Service() {

    private lateinit var stepSensor: StepSensor
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private var hapticJob: Job? = null
    private var lastHapticAt: Long = 0L
    private val vibrator: Vibrator? by lazy { resolveVibrator() }

    override fun onCreate() {
        super.onCreate()
        val budget = MovementBudget.get(applicationContext)
        stepSensor = StepSensor(applicationContext, budget)
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildNotification())
        val ok = stepSensor.register()
        if (!ok) Log.w(TAG, "step counter unavailable on this device — service idle")
        hapticJob = scope.launch {
            budget.creditedTiles.collect { _ ->
                if (!budget.hapticOnStep.value) return@collect
                val now = SystemClock.uptimeMillis()
                if (now - lastHapticAt < HAPTIC_MIN_GAP_MS) return@collect
                lastHapticAt = now
                pulseVibrator()
            }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_STICKY

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        stepSensor.unregister()
        hapticJob?.cancel()
        scope.cancel()
        super.onDestroy()
    }

    private fun resolveVibrator(): Vibrator? = try {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            (getSystemService(VIBRATOR_MANAGER_SERVICE) as? VibratorManager)?.defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            getSystemService(VIBRATOR_SERVICE) as? Vibrator
        }
    } catch (e: Exception) {
        Log.w(TAG, "no vibrator available", e); null
    }

    private fun pulseVibrator() {
        val v = vibrator ?: return
        if (!v.hasVibrator()) return
        v.vibrate(VibrationEffect.createOneShot(HAPTIC_PULSE_MS, VibrationEffect.DEFAULT_AMPLITUDE))
    }

    private fun createNotificationChannel() {
        val nm = getSystemService(NotificationManager::class.java)
        if (nm.getNotificationChannel(CHANNEL_ID) == null) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Step counter",
                NotificationManager.IMPORTANCE_LOW,
            ).apply {
                description = "Tracks real-world steps for in-game movement"
                setShowBadge(false)
            }
            nm.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(): Notification {
        val tapIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, EmulatorActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_SINGLE_TOP
            },
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("PokéTrek")
            .setContentText("Counting steps")
            .setSmallIcon(android.R.drawable.ic_menu_compass)
            .setOngoing(true)
            .setContentIntent(tapIntent)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .build()
    }

    companion object {
        fun start(context: Context) {
            val intent = Intent(context, StepCounterService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }
    }
}
