package com.poketrek

import android.net.Uri
import android.os.Build
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
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import com.poketrek.emu.CalibrationStore
import com.poketrek.emu.EmulatorRunner
import com.poketrek.emu.SaveStateStore
import com.poketrek.step.MovementBudget
import com.poketrek.step.StepCounterService

private const val TAG = "EmulatorActivity"

class EmulatorActivity : ComponentActivity() {

    private lateinit var budget: MovementBudget
    private lateinit var runner: EmulatorRunner
    private lateinit var saveStateStore: SaveStateStore

    private val requestActivityRecognition = registerForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted ->
        if (granted) {
            StepCounterService.start(applicationContext)
        } else {
            Log.w(TAG, "ACTIVITY_RECOGNITION denied — step counter unavailable")
        }
    }

    private val requestPostNotifications = registerForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { /* result ignored — service still runs without it on Android 13+ */ }

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
        WindowCompat.setDecorFitsSystemWindows(window, false)
        WindowCompat.getInsetsController(window, window.decorView).apply {
            hide(WindowInsetsCompat.Type.systemBars())
            systemBarsBehavior =
                WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        }
        budget = MovementBudget.get(applicationContext)
        runner = EmulatorRunner(budget, CalibrationStore(applicationContext))
        saveStateStore = SaveStateStore(applicationContext)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
            && checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)
            != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            requestPostNotifications.launch(android.Manifest.permission.POST_NOTIFICATIONS)
        }
        if (checkSelfPermission(android.Manifest.permission.ACTIVITY_RECOGNITION)
            == android.content.pm.PackageManager.PERMISSION_GRANTED) {
            StepCounterService.start(applicationContext)
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
                        getSaveSlots = saveStateStore::slots,
                        onSaveSlot = { slot ->
                            runner.saveState()?.let { saveStateStore.save(slot, it) } ?: false
                        },
                        onLoadSlot = { slot ->
                            saveStateStore.load(slot)?.let { runner.loadState(it) } ?: false
                        },
                    )
                }
            }
            DisposableEffect(Unit) {
                onDispose { runner.stop() }
            }
        }
    }

    override fun onStart() {
        super.onStart()
        runner.resume()
    }

    override fun onStop() {
        runner.pause()
        super.onStop()
    }

    override fun onDestroy() {
        runner.stop()
        super.onDestroy()
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) {
            WindowCompat.getInsetsController(window, window.decorView)
                .hide(WindowInsetsCompat.Type.systemBars())
        }
    }
}

@Composable
private fun AppRoot(
    runner: EmulatorRunner,
    budget: MovementBudget,
    onPickRom: () -> Unit,
    onDebugAddSteps: (Int) -> Unit,
    getSaveSlots: () -> List<com.poketrek.emu.SaveStateStore.Slot>,
    onSaveSlot: (Int) -> Boolean,
    onLoadSlot: (Int) -> Boolean,
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
            onPickRom = onPickRom,
            getSaveSlots = getSaveSlots,
            onSaveSlot = onSaveSlot,
            onLoadSlot = onLoadSlot,
            modifier = Modifier.fillMaxSize().padding(8.dp),
        )
    }
}
