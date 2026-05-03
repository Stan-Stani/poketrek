package com.poketrek

import android.net.Uri
import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.poketrek.emu.EmulatorRunner
import com.poketrek.step.MovementBudget
import com.poketrek.step.StepSensor

private const val TAG = "EmulatorActivity"

class EmulatorActivity : ComponentActivity() {

    private lateinit var budget: MovementBudget
    private lateinit var runner: EmulatorRunner
    private var stepSensor: StepSensor? = null

    private val requestActivityRecognition = registerForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted ->
        if (granted) {
            stepSensor?.register()
        } else {
            Log.w(TAG, "ACTIVITY_RECOGNITION denied — step counter unavailable")
        }
    }

    private val pickRom = registerForActivityResult(
        ActivityResultContracts.OpenDocument(),
    ) { uri: Uri? ->
        if (uri == null) return@registerForActivityResult
        try {
            contentResolver.takePersistableUriPermission(
                uri,
                android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION,
            )
        } catch (e: SecurityException) {
            Log.w(TAG, "Could not persist URI permission", e)
        }
        val bytes = contentResolver.openInputStream(uri)?.use { it.readBytes() }
        if (bytes != null) {
            runner.loadRom(bytes)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        budget = MovementBudget(applicationContext)
        runner = EmulatorRunner(budget)
        stepSensor = StepSensor(applicationContext, budget)

        if (checkSelfPermission(android.Manifest.permission.ACTIVITY_RECOGNITION)
            == android.content.pm.PackageManager.PERMISSION_GRANTED) {
            stepSensor?.register()
        } else {
            requestActivityRecognition.launch(android.Manifest.permission.ACTIVITY_RECOGNITION)
        }

        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    AppRoot(
                        runner = runner,
                        budget = budget,
                        onPickRom = { pickRom.launch(arrayOf("application/octet-stream", "*/*")) },
                        onDebugAddSteps = budget::debugAddSteps,
                    )
                }
            }
            DisposableEffect(Unit) {
                onDispose { runner.stop() }
            }
        }
    }

    override fun onDestroy() {
        stepSensor?.unregister()
        runner.stop()
        super.onDestroy()
    }
}

@Composable
private fun AppRoot(
    runner: EmulatorRunner,
    budget: MovementBudget,
    onPickRom: () -> Unit,
    onDebugAddSteps: (Int) -> Unit,
) {
    val romLoaded by runner.romLoaded
    if (!romLoaded) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Column(
                verticalArrangement = Arrangement.spacedBy(16.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text("PokéTrek", style = MaterialTheme.typography.headlineMedium)
                Text("Pick a LeafGreen ROM (.gba) to begin")
                Button(onClick = onPickRom) { Text("Choose ROM") }
            }
        }
    } else {
        com.poketrek.ui.EmulatorScreen(
            runner = runner,
            budget = budget,
            onDebugAddSteps = onDebugAddSteps,
            modifier = Modifier.fillMaxSize().padding(8.dp),
        )
    }
}
