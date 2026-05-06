package com.poketrek.emu

import android.content.Context
import android.util.Log
import java.io.File

private const val TAG = "SaveStateStore"

/** Legacy single-slot file from before multi-slot landed; auto-migrated into slot 1. */
private const val FILENAME_LEGACY = "savestate.bin"
private const val SLOTS_DIR = "savestates"
private const val SLOT_FILE_PREFIX = "slot_"
private const val SLOT_FILE_SUFFIX = ".bin"
/** Sidecar holding the source ROM's CRC32 (lowercase hex, no prefix). */
private const val SLOT_META_SUFFIX = ".meta"

/** Number of save slots the UI exposes. Bump along with the settings UI if growing. */
const val NUM_SAVE_SLOTS = 3

/**
 * Persistent save-state store with [NUM_SAVE_SLOTS] independent slots.
 *
 * Each slot is a single file under `filesDir/savestates/slot_N.bin`. The
 * file's `lastModified()` doubles as the slot's timestamp — no separate
 * metadata file. An empty/missing file means the slot is unused.
 *
 * On first use, the legacy single-slot `savestate.bin` (if present) is
 * migrated into slot 1 so users don't lose their existing save.
 */
class SaveStateStore(private val context: Context) {

    /**
     * @param savedAt epoch millis when the slot was last written, or null
     *   if the slot is empty.
     * @param romCrc32 CRC32 of the ROM that produced this save, or null for
     *   legacy slots written before metadata was tracked.
     */
    data class Slot(
        val index: Int,
        val savedAt: Long?,
        val romCrc32: Long?,
    ) {
        val isEmpty: Boolean get() = savedAt == null
    }

    private val slotsDir: File
        get() = File(context.filesDir, SLOTS_DIR).also { it.mkdirs() }

    private fun slotFile(index: Int): File =
        File(slotsDir, "$SLOT_FILE_PREFIX$index$SLOT_FILE_SUFFIX")

    private fun metaFile(index: Int): File =
        File(slotsDir, "$SLOT_FILE_PREFIX$index$SLOT_META_SUFFIX")

    private fun readSlotCrc(index: Int): Long? {
        val mf = metaFile(index)
        if (!mf.exists() || mf.length() == 0L) return null
        return try {
            mf.readText().trim().toLong(16)
        } catch (e: Exception) {
            Log.w(TAG, "slot $index meta unreadable", e)
            null
        }
    }

    init { migrateLegacyIfNeeded() }

    private fun migrateLegacyIfNeeded() {
        val legacy = File(context.filesDir, FILENAME_LEGACY)
        if (!legacy.exists() || legacy.length() == 0L) return
        val target = slotFile(1)
        try {
            slotsDir.mkdirs()
            if (!target.exists() || target.length() == 0L) {
                legacy.copyTo(target, overwrite = true)
            }
            legacy.delete()
            Log.i(TAG, "migrated legacy save state into slot 1")
        } catch (e: Exception) {
            Log.w(TAG, "legacy save migration failed", e)
        }
    }

    fun slots(): List<Slot> = (1..NUM_SAVE_SLOTS).map { i ->
        val f = slotFile(i)
        if (f.exists() && f.length() > 0) {
            Slot(i, f.lastModified(), readSlotCrc(i))
        } else {
            Slot(i, null, null)
        }
    }

    fun hasSave(slot: Int): Boolean {
        val f = slotFile(slot)
        return f.exists() && f.length() > 0
    }

    /**
     * Persists [bytes] into [slot]. When [romCrc32] is non-null the source
     * ROM's CRC is recorded alongside so the UI can later display the
     * variant and prevent loading a save into an incompatible ROM. Passing
     * null deletes any existing sidecar (slot becomes "ROM unknown").
     */
    fun save(slot: Int, bytes: ByteArray, romCrc32: Long? = null): Boolean {
        require(slot in 1..NUM_SAVE_SLOTS) { "slot out of range: $slot" }
        return try {
            slotFile(slot).writeBytes(bytes)
            val mf = metaFile(slot)
            if (romCrc32 != null) {
                mf.writeText(romCrc32.toString(16))
            } else if (mf.exists()) {
                mf.delete()
            }
            true
        } catch (e: Exception) {
            Log.e(TAG, "save slot $slot failed", e)
            false
        }
    }

    fun load(slot: Int): ByteArray? {
        require(slot in 1..NUM_SAVE_SLOTS) { "slot out of range: $slot" }
        return try {
            val f = slotFile(slot)
            if (!f.exists() || f.length() == 0L) null else f.readBytes()
        } catch (e: Exception) {
            Log.e(TAG, "load slot $slot failed", e)
            null
        }
    }
}
