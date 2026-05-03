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

private const val TAG = "EmulatorActivity"

class EmulatorActivity : ComponentActivity() {

    private val runner = EmulatorRunner()

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
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    AppRoot(
                        runner = runner,
                        onPickRom = { pickRom.launch(arrayOf("application/octet-stream", "*/*")) },
                    )
                }
            }
            DisposableEffect(Unit) {
                onDispose { runner.stop() }
            }
        }
    }

    override fun onDestroy() {
        runner.stop()
        super.onDestroy()
    }
}

@Composable
private fun AppRoot(
    runner: EmulatorRunner,
    onPickRom: () -> Unit,
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
            modifier = Modifier.fillMaxSize().padding(8.dp),
        )
    }
}
