package com.poketrek.emu

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking

/**
 * DataStore-backed persistence for per-ROM [RomCalibration] entries,
 * keyed by ROM CRC32. Reads are blocking on purpose — calibrations are
 * loaded once at ROM-load time on the emu thread, not in the frame loop.
 *
 * Schema is one int preference per (rom-crc, field) tuple so adding new
 * calibrated fields later doesn't invalidate existing entries:
 *   "rom_<crc8hex>_sb1ptr" → saveBlock1PtrAddr
 */
class CalibrationStore(private val context: Context) {

    private fun crcHex(crc32: Long): String =
        crc32.toString(16).uppercase().padStart(8, '0')

    private fun sb1Key(crc32: Long) =
        intPreferencesKey("rom_${crcHex(crc32)}_sb1ptr")

    /**
     * Reads the persisted calibration for [crc32]. Falls back to the
     * built-in US Rev 1 entry when [crc32] matches that ROM's CRC and no
     * override is stored, so the canonical ROM works without prior
     * calibration. Returns null for unknown ROMs that haven't been
     * calibrated yet.
     */
    fun load(crc32: Long): RomCalibration? = runBlocking {
        val prefs = context.calibrationStore.data.first()
        val sb1 = prefs[sb1Key(crc32)]
        if (sb1 != null) {
            RomCalibration(saveBlock1PtrAddr = sb1)
        } else if (crc32 == US_REV1_CRC) {
            RomCalibration.DEFAULT_US_REV1
        } else {
            null
        }
    }

    suspend fun save(crc32: Long, calibration: RomCalibration) {
        context.calibrationStore.edit { prefs ->
            prefs[sb1Key(crc32)] = calibration.saveBlock1PtrAddr
        }
    }

    suspend fun clear(crc32: Long) {
        context.calibrationStore.edit { prefs ->
            prefs.remove(sb1Key(crc32))
        }
    }

    companion object {
        private const val US_REV1_CRC = 0xDAFFECECL
    }
}

private val Context.calibrationStore by preferencesDataStore("rom_calibrations")
