package com.poketrek.emu

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.FileNotFoundException
import java.util.zip.CRC32

/**
 * Verifies the native xdelta decoder ([NativeEmulator.applyXdelta]) reproduces
 * the 2024 Korean fan-translation ROM on-device, byte-for-byte, the same way
 * the host-side proof did.
 *
 * Setup (both gitignored — drop manually before `connectedDebugAndroidTest`):
 *   app/src/androidTest/assets/leafgreen_jp.gba    — JP LeafGreen 1.0 base
 *                                                    (MD5 138a71a5…fc7)
 *   app/src/androidTest/assets/leafgreen_J-K.xdelta — the 2024-02-29 patch
 *
 * The test is skipped (not failed) when those assets are absent, so it doesn't
 * break runs that only carry the Phase 0 leafgreen.gba.
 */
@RunWith(AndroidJUnit4::class)
class XdeltaPatchTest {

    private val expectedCrc32 = 0x4A38A8CBL

    @Test
    fun appliesKoreanPatchToCanonicalBase() {
        val base = readAssetOrNull("leafgreen_jp.gba")
        val patch = readAssetOrNull("leafgreen_J-K.xdelta")
        assumeTrue(
            "drop leafgreen_jp.gba + leafgreen_J-K.xdelta into androidTest/assets",
            base != null && patch != null,
        )

        val emu = NativeEmulator()
        val patched = emu.applyXdelta(base!!, patch!!)

        assertNotNull("applyXdelta returned null — decode failed", patched)
        assertEquals("patched ROM size", 16 * 1024 * 1024, patched!!.size)

        val crc = CRC32().apply { update(patched) }.value
        assertEquals(
            "patched ROM CRC32 must match the canonical 2024 KR ROM",
            expectedCrc32,
            crc,
        )
    }

    private fun readAssetOrNull(name: String): ByteArray? {
        val ctx = InstrumentationRegistry.getInstrumentation().context
        return try {
            ctx.assets.open(name).use { it.readBytes() }
        } catch (_: FileNotFoundException) {
            null
        }
    }
}
