package com.poketrek.emu

import android.content.Context
import android.util.Log
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * On-device cache of previously-picked ROMs, keyed by CRC32 so a given ROM
 * is only stored once. Files live under filesDir/roms/<crc32>.gba; the index
 * (label, size, last-used time) is in a SharedPreferences entry so the
 * settings UI can present a library list without re-reading every file.
 *
 * The cache exists so the user only has to navigate the SAF picker once
 * per ROM; on launch we auto-load the most-recently-used cached ROM and
 * the settings sheet exposes a tap-to-switch list of all cached entries.
 */
class RomCache(private val ctx: Context) {

    data class Slot(
        val crc32: Long,
        val label: String,
        val sizeBytes: Long,
        val lastUsedAtMs: Long,
    )

    private fun prefs() = ctx.getSharedPreferences("rom_cache", Context.MODE_PRIVATE)

    private fun dir(): File = File(ctx.filesDir, "roms").also { it.mkdirs() }

    private fun fileFor(crc32: Long) = File(dir(), "%08x.gba".format(crc32))

    fun list(): List<Slot> = readIndex().sortedByDescending { it.lastUsedAtMs }

    fun mostRecent(): Slot? = list().firstOrNull()

    fun put(bytes: ByteArray, crc32: Long, label: String): Slot {
        try {
            fileFor(crc32).writeBytes(bytes)
        } catch (e: Exception) {
            Log.w(TAG, "Failed to write ROM bytes", e)
        }
        val now = System.currentTimeMillis()
        val slot = Slot(crc32, label, bytes.size.toLong(), now)
        val updated = readIndex().filterNot { it.crc32 == crc32 } + slot
        writeIndex(updated)
        return slot
    }

    fun load(crc32: Long): ByteArray? {
        val f = fileFor(crc32)
        if (!f.exists()) return null
        val bytes = try {
            f.readBytes()
        } catch (e: Exception) {
            Log.w(TAG, "Failed to read cached ROM", e)
            return null
        }
        bumpLastUsed(crc32)
        return bytes
    }

    fun remove(crc32: Long) {
        fileFor(crc32).delete()
        writeIndex(readIndex().filterNot { it.crc32 == crc32 })
    }

    private fun bumpLastUsed(crc32: Long) {
        val now = System.currentTimeMillis()
        val updated = readIndex().map {
            if (it.crc32 == crc32) it.copy(lastUsedAtMs = now) else it
        }
        writeIndex(updated)
    }

    private fun readIndex(): List<Slot> {
        val s = prefs().getString("index", null) ?: return emptyList()
        return try {
            val arr = JSONArray(s)
            (0 until arr.length()).mapNotNull { i ->
                val o = arr.getJSONObject(i)
                Slot(
                    crc32 = o.getLong("crc32"),
                    label = o.getString("label"),
                    sizeBytes = o.getLong("size"),
                    lastUsedAtMs = o.getLong("lastUsedAt"),
                ).takeIf { fileFor(it.crc32).exists() }
            }
        } catch (e: Exception) {
            Log.w(TAG, "ROM cache index unreadable; resetting", e)
            emptyList()
        }
    }

    private fun writeIndex(slots: List<Slot>) {
        val arr = JSONArray()
        for (s in slots) {
            arr.put(
                JSONObject().apply {
                    put("crc32", s.crc32)
                    put("label", s.label)
                    put("size", s.sizeBytes)
                    put("lastUsedAt", s.lastUsedAtMs)
                },
            )
        }
        prefs().edit().putString("index", arr.toString()).apply()
    }

    private companion object { const val TAG = "RomCache" }
}
