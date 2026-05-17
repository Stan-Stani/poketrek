package com.poketrek.emu

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.FileNotFoundException
import java.util.zip.CRC32

/**
 * Full on-device exercise of [KoreanRomPatcher.produce]: real Drive
 * download (the authors' public patch bundle), real zip extraction
 * (cp437→utf8 entry-name recovery), real native xdelta decode, real
 * CRC32 gate. This is the part the JVM `KoreanRomPatcherTest` stubs out
 * — here nothing is injected, so a green run means the actual user flow
 * works minus the SAF file-picker tap.
 *
 * Setup (gitignored — drop before `connectedDebugAndroidTest`):
 *   app/src/androidTest/assets/leafgreen_jp.gba — JP LeafGreen 1.0 base
 *                                                 (MD5 138a71a5…fc7)
 * No patch asset needed: fetching it from Drive is exactly what we're
 * verifying. Skipped (not failed) when the base asset is absent, and
 * requires network on the test device.
 */
@RunWith(AndroidJUnit4::class)
class KoreanRomPatcherE2ETest {

    @Test
    fun producesKoreanRomFromJpBaseViaRealDownload() {
        val base = readAssetOrNull("leafgreen_jp.gba")
        assumeTrue(
            "drop leafgreen_jp.gba (JP LeafGreen 1.0) into androidTest/assets",
            base != null,
        )

        val ctx = InstrumentationRegistry.getInstrumentation().targetContext
        val emu = NativeEmulator()
        val phases = mutableListOf<KoreanRomPatcher.Phase>()

        val result = KoreanRomPatcher.produce(
            baseBytes = base!!,
            cacheDir = ctx.cacheDir,
            applyXdelta = emu::applyXdelta,
            onPhase = { phases.add(it) },
        )

        val patched = result.getOrElse {
            throw AssertionError("produce() failed: ${it.message}", it)
        }
        assertEquals("patched ROM size", 16 * 1024 * 1024, patched.size)
        val crc = CRC32().apply { update(patched) }.value
        assertEquals(
            "patched ROM CRC32 must be the canonical 2024 KR ROM",
            KoreanRomPatcher.EXPECTED_CRC32,
            crc,
        )
        assertEquals(RomVariant.LEAFGREEN_KR_2024, RomIdentity.variantFor(crc))
        assertTrue(
            "should have reported a download phase",
            phases.contains(KoreanRomPatcher.Phase.DOWNLOADING_PATCH),
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
