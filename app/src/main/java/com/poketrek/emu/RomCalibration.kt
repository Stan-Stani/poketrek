package com.poketrek.emu

/**
 * Per-ROM RAM offsets the gating logic needs. For US Rev 1 these are
 * known constants; for Korean / unknown builds they are discovered at
 * runtime by [RomCalibrator].
 *
 * Only [saveBlock1PtrAddr] is calibrated today — the other LeafGreenRam
 * offsets (moving status, speed/biking) are read from [DEFAULT_US_REV1]
 * fallbacks until those probes are added too.
 */
data class RomCalibration(
    val saveBlock1PtrAddr: Int,
) {
    companion object {
        /** Hardcoded for the canonical US Rev 1 build (CRC 0xDAFFECEC). */
        val DEFAULT_US_REV1 = RomCalibration(
            saveBlock1PtrAddr = LeafGreenRam.SAVE_BLOCK1_PTR,
        )
    }
}
