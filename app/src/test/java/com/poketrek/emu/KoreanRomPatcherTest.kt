package com.poketrek.emu

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.ByteArrayOutputStream
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

class KoreanRomPatcherTest {

    /**
     * Reproduces the zip-reader mojibake: the bundle's entry names are
     * UTF-8 bytes with no language-encoding flag, so a Cp437 reader hands
     * back the UTF-8 bytes reinterpreted as Cp437. Cp437 is a complete
     * bijective single-byte charset, so this round-trips.
     */
    private fun asCp437Mojibake(realName: String): String =
        String(realName.toByteArray(Charsets.UTF_8), charset("Cp437"))

    @Test fun selectsLeafgreenAmongCleanUtf8Names() {
        val names = listOf(
            "가이드.txt",
            "포켓몬스터 파이어레드 패치.xdelta",
            "포켓몬스터 리프그린 패치.xdelta",
            "포켓몬스터 에메랄드 패치.xdelta",
        )
        assertEquals("포켓몬스터 리프그린 패치.xdelta", KoreanRomPatcher.selectLeafgreenEntryName(names))
    }

    @Test fun selectsLeafgreenThroughCp437Mojibake() {
        // What Java's ZipInputStream(Cp437) actually yields for a no-EFS-flag
        // archive — the case Python's zipfile hits too.
        val names = listOf(
            asCp437Mojibake("리프그린 J-K.xdelta"),
            asCp437Mojibake("파이어레드 J-K.xdelta"),
            asCp437Mojibake("에메랄드 J-K.xdelta"),
            asCp437Mojibake("README_가이드.txt"),
        )
        val picked = KoreanRomPatcher.selectLeafgreenEntryName(names)
        assertEquals(asCp437Mojibake("리프그린 J-K.xdelta"), picked)
        // And it's recoverable back to the real Korean name.
        assertEquals(
            "리프그린 J-K.xdelta",
            String(picked!!.toByteArray(charset("Cp437")), Charsets.UTF_8),
        )
    }

    @Test fun returnsNullWhenNoLeafgreenXdelta() {
        val names = listOf("파이어레드.xdelta", "에메랄드.xdelta", "리프그린.txt")
        assertNull(KoreanRomPatcher.selectLeafgreenEntryName(names))
    }

    @Test fun extractsLeafgreenBytesFromBundleZip() {
        val lgBytes = "LEAFGREEN-XDELTA-PAYLOAD".toByteArray()
        val zip = ByteArrayOutputStream().also { bos ->
            ZipOutputStream(bos).use { zos ->
                fun put(name: String, data: ByteArray) {
                    zos.putNextEntry(ZipEntry(name))
                    zos.write(data)
                    zos.closeEntry()
                }
                put("포켓몬스터 파이어레드.xdelta", "FIRERED".toByteArray())
                put("포켓몬스터 리프그린.xdelta", lgBytes)
                put("포켓몬스터 에메랄드.xdelta", "EMERALD".toByteArray())
                put("README_가이드.txt", "guide".toByteArray())
            }
        }.toByteArray()

        assertArrayEquals(lgBytes, KoreanRomPatcher.extractLeafgreenXdelta(zip))
    }

    @Test fun isExpectedKoreanRomRejectsWrongSize() {
        assertFalse(KoreanRomPatcher.isExpectedKoreanRom(ByteArray(1024)))
        assertFalse(
            KoreanRomPatcher.isExpectedKoreanRom(
                ByteArray(KoreanRomPatcher.EXPECTED_SIZE_BYTES - 1),
            ),
        )
    }

    @Test fun isExpectedKoreanRomRejectsRightSizeWrongCrc() {
        // All-zero 16 MiB: correct size, definitely not the KR_2024 CRC.
        assertFalse(
            KoreanRomPatcher.isExpectedKoreanRom(
                ByteArray(KoreanRomPatcher.EXPECTED_SIZE_BYTES),
            ),
        )
    }

    @Test fun expectedCrcMapsToKr2024Variant() {
        // The patcher's success gate must agree with RomIdentity, or a
        // correctly produced ROM would be cached then rejected on reload.
        assertEquals(
            RomVariant.LEAFGREEN_KR_2024,
            RomIdentity.variantFor(KoreanRomPatcher.EXPECTED_CRC32),
        )
        assertEquals(0x1000000, KoreanRomPatcher.EXPECTED_SIZE_BYTES)
    }
}
