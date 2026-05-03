package com.poketrek.emu

import android.content.Context
import android.util.Log
import java.io.File

private const val TAG = "SaveStateStore"
private const val FILENAME = "savestate.bin"

/**
 * Single-slot persistent save state store. Phase 5 polish can extend to
 * multiple timestamped slots.
 */
class SaveStateStore(private val context: Context) {
    private val file: File
        get() = File(context.filesDir, FILENAME)

    fun hasSave(): Boolean = file.exists() && file.length() > 0

    fun save(bytes: ByteArray): Boolean {
        return try {
            file.writeBytes(bytes)
            true
        } catch (e: Exception) {
            Log.e(TAG, "save failed", e)
            false
        }
    }

    fun load(): ByteArray? {
        return try {
            if (!hasSave()) null else file.readBytes()
        } catch (e: Exception) {
            Log.e(TAG, "load failed", e)
            null
        }
    }
}
