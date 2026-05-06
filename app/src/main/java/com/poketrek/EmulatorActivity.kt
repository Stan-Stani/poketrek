package com.poketrek

import android.content.pm.ActivityInfo
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.view.OrientationEventListener
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
import androidx.compose.runtime.MutableState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import android.provider.OpenableColumns
import com.poketrek.emu.CalibrationStore
import com.poketrek.emu.EmulatorRunner
import com.poketrek.emu.RomCache
import com.poketrek.emu.SaveStateStore
import com.poketrek.moneo.MoneoModule
import com.poketrek.moneo.gate.MoneoSoftGate
import com.poketrek.step.MovementBudget
import com.poketrek.step.StepCounterService

private const val TAG = "EmulatorActivity"

class EmulatorActivity : ComponentActivity() {

    private lateinit var budget: MovementBudget
    private lateinit var runner: EmulatorRunner
    private lateinit var saveStateStore: SaveStateStore
    private lateinit var moneo: MoneoModule
    private lateinit var moneoGate: MoneoSoftGate
    private lateinit var romCache: RomCache

    // Orientation lock + manual flip. The activity is locked (no sensor
    // follow) but we listen to OrientationEventListener purely to detect when
    // the user is *trying* to rotate between landscape and portrait, and
    // surface a one-tap "switch" prompt in that case. Portrait is mainly
    // useful for the Moneo card-review overlay.
    private var portraitLocked = false
    private val showFlipPrompt: MutableState<Boolean> = mutableStateOf(false)
    private var orientListener: OrientationEventListener? = null

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
        if (bytes != null && runner.loadRom(bytes)) {
            val identity = runner.romIdentity.value ?: return@registerForActivityResult
            val label = displayNameFor(uri)
                ?: identity.variant.displayName.takeIf { it.isNotBlank() }
                ?: "ROM ${identity.crc32Hex}"
            romCache.put(bytes, identity.crc32, label)
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
        moneo = MoneoModule.get(applicationContext)
        moneo.bindCapture { addr, length -> runner.busReadBytes(addr, length) }
        moneoGate = MoneoSoftGate(moneo.repository, moneo.prefs)
        romCache = RomCache(applicationContext)

        // Manual orientation: locked to landscape (manifest), no sensor follow.
        // A floating "flip" prompt only appears when OrientationEventListener
        // sees the phone being held in the opposite landscape — see init below.
        applyPersistedOrientation()
        installOrientationFlipDetector()

        // If a previously-picked ROM is cached in private storage, load it
        // so the user doesn't have to re-pick from Downloads on every launch.
        loadCachedRomIfPresent()

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
                        moneo = moneo,
                        moneoGate = moneoGate,
                        onPickRom = { pickRom.launch(arrayOf("application/octet-stream", "*/*")) },
                        onDebugAddSteps = budget::debugAddSteps,
                        getSaveSlots = saveStateStore::slots,
                        onSaveSlot = { slot ->
                            runner.saveState()?.let {
                                saveStateStore.save(slot, it, runner.romIdentity.value?.crc32)
                            } ?: false
                        },
                        onLoadSlot = { slot ->
                            saveStateStore.load(slot)?.let { runner.loadState(it) } ?: false
                        },
                        showFlipPrompt = showFlipPrompt.value,
                        flipTargetIsPortrait = !portraitLocked,
                        onFlipOrientation = ::flipOrientation,
                        getRomLibrary = romCache::list,
                        currentRomCrc32 = { runner.romIdentity.value?.crc32 },
                        onLoadCachedRom = ::loadCachedRom,
                        onRemoveCachedRom = romCache::remove,
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
        orientListener?.enable()
    }

    override fun onStop() {
        runner.pause()
        orientListener?.disable()
        showFlipPrompt.value = false
        super.onStop()
    }

    override fun onDestroy() {
        runner.stop()
        super.onDestroy()
    }

    private fun uiPrefs() = getSharedPreferences("ui", MODE_PRIVATE)

    private fun loadCachedRomIfPresent() {
        val recent = romCache.mostRecent() ?: return
        loadCachedRom(recent.crc32)
    }

    private fun loadCachedRom(crc32: Long): Boolean {
        val bytes = romCache.load(crc32) ?: run {
            romCache.remove(crc32)
            return false
        }
        return if (runner.loadRom(bytes)) {
            true
        } else {
            Log.w(TAG, "Cached ROM ${"0x" + crc32.toString(16)} failed to load; removing")
            romCache.remove(crc32)
            false
        }
    }

    private fun displayNameFor(uri: Uri): String? = try {
        contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)
            ?.use { c -> if (c.moveToFirst()) c.getString(0) else null }
            ?.removeSuffix(".gba")
    } catch (e: Exception) {
        Log.w(TAG, "Failed to query display name", e)
        null
    }

    private fun applyPersistedOrientation() {
        portraitLocked = uiPrefs().getBoolean("orient_portrait", false)
        requestedOrientation = if (portraitLocked) {
            ActivityInfo.SCREEN_ORIENTATION_PORTRAIT
        } else {
            ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
        }
    }

    private fun installOrientationFlipDetector() {
        // OrientationEventListener emits 0..359 with 0° = device's natural
        // orientation (portrait on phones), ~90°/270° = landscape. Show the
        // prompt only when the device is being held perpendicular to the
        // current lock — i.e. landscape is locked but device is portrait, or
        // vice versa.
        orientListener = object : OrientationEventListener(this) {
            override fun onOrientationChanged(degrees: Int) {
                if (degrees == ORIENTATION_UNKNOWN) return
                val portraitHeld = degrees <= 30 || degrees >= 330 ||
                    (degrees in 150..210)
                val landscapeHeld = (degrees in 60..120) || (degrees in 240..300)
                val perpendicular = if (portraitLocked) landscapeHeld else portraitHeld
                if (showFlipPrompt.value != perpendicular) {
                    showFlipPrompt.value = perpendicular
                }
            }
        }.also { if (it.canDetectOrientation()) it.enable() else it.disable() }
    }

    private fun flipOrientation() {
        portraitLocked = !portraitLocked
        uiPrefs().edit().putBoolean("orient_portrait", portraitLocked).apply()
        requestedOrientation = if (portraitLocked) {
            ActivityInfo.SCREEN_ORIENTATION_PORTRAIT
        } else {
            ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
        }
        showFlipPrompt.value = false
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
    moneo: MoneoModule,
    moneoGate: MoneoSoftGate,
    onPickRom: () -> Unit,
    onDebugAddSteps: (Int) -> Unit,
    getSaveSlots: () -> List<com.poketrek.emu.SaveStateStore.Slot>,
    onSaveSlot: (Int) -> Boolean,
    onLoadSlot: (Int) -> Boolean,
    showFlipPrompt: Boolean,
    flipTargetIsPortrait: Boolean,
    onFlipOrientation: () -> Unit,
    getRomLibrary: () -> List<com.poketrek.emu.RomCache.Slot>,
    currentRomCrc32: () -> Long?,
    onLoadCachedRom: (Long) -> Boolean,
    onRemoveCachedRom: (Long) -> Unit,
) {
    val romLoaded by runner.romLoaded
    Box(modifier = Modifier.fillMaxSize()) {
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
                moneo = moneo,
                moneoGate = moneoGate,
                onDebugAddSteps = onDebugAddSteps,
                onPickRom = onPickRom,
                getSaveSlots = getSaveSlots,
                onSaveSlot = onSaveSlot,
                onLoadSlot = onLoadSlot,
                getRomLibrary = getRomLibrary,
                currentRomCrc32 = currentRomCrc32,
                onLoadCachedRom = onLoadCachedRom,
                onRemoveCachedRom = onRemoveCachedRom,
                modifier = Modifier.fillMaxSize().padding(8.dp),
            )
        }
        if (showFlipPrompt) {
            Button(
                onClick = onFlipOrientation,
                modifier = Modifier
                    .align(Alignment.TopCenter)
                    .padding(top = 12.dp),
            ) {
                Text(if (flipTargetIsPortrait) "Switch to portrait" else "Switch to landscape")
            }
        }
    }
}
