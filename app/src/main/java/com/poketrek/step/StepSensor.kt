package com.poketrek.step

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.util.Log

private const val TAG = "StepSensor"

/**
 * Wraps Sensor.TYPE_STEP_COUNTER and feeds cumulative-step values into a
 * [MovementBudget]. The counter is monotonic since boot — [MovementBudget]
 * is responsible for delta computation and reboot rebasing.
 *
 * Callers must hold the ACTIVITY_RECOGNITION permission before calling
 * [register] on Android 10+. The Android Emulator does not expose this
 * sensor; on emulators [register] returns false.
 */
class StepSensor(private val context: Context, private val budget: MovementBudget) :
    SensorEventListener {

    private val sensorManager: SensorManager =
        context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private var sensor: Sensor? = null

    /** Returns true if the sensor was found and registered. */
    fun register(): Boolean {
        val s = sensorManager.getDefaultSensor(Sensor.TYPE_STEP_COUNTER)
        if (s == null) {
            Log.w(TAG, "TYPE_STEP_COUNTER not available on this device")
            return false
        }
        sensor = s
        return sensorManager.registerListener(this, s, SensorManager.SENSOR_DELAY_NORMAL)
    }

    fun unregister() {
        sensorManager.unregisterListener(this)
    }

    override fun onSensorChanged(event: SensorEvent) {
        if (event.sensor.type != Sensor.TYPE_STEP_COUNTER) return
        val cumulative = event.values[0].toLong()
        budget.onSensorValue(cumulative)
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit
}
