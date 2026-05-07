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

        /**
         * Hardcoded for the 2024-02-29 Korean patch (CRC 0x4A38A8CB). Null
         * until harvested — to populate, run the in-app calibration UI once
         * on a device with this exact ROM, then check logcat for a line like
         *   `EmulatorRunner: calibrated 0x4A38A8CB: sb1Ptr=0x3005xxx`
         * and replace null with `RomCalibration(saveBlock1PtrAddr = 0x3005xxx)`.
         * Once populated, [CalibrationStore.load] returns this for the KR_2024
         * CRC when no per-device override is stored, so users with this ROM
         * skip the calibration UI entirely. Other Korean ROM patches (different
         * CRC) still go through manual calibration.
         */
        val DEFAULT_KR_2024: RomCalibration? = null
    }
}
