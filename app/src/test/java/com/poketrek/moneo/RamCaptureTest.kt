package com.poketrek.moneo

import com.poketrek.moneo.corpus.RamCapture
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.nio.file.Files

class RamCaptureTest {

    private class FakeReader(private val frames: List<ByteArray>) : RamCapture.BusReader {
        var idx = 0
        override fun readBytes(addr: Int, length: Int): ByteArray? {
            if (idx >= frames.size) return null
            return frames[idx++].copyOf(length)
        }
    }

    @Test fun captureRunsDetectedFromDiff() {
        // Build two EWRAM-sized "frames" where the second has a 30-byte
        // contiguous run of new bytes inserted at offset 1000.
        val size = RamCapture.EWRAM_SIZE
        val frame0 = ByteArray(size) // all zeros
        val frame1 = frame0.copyOf()
        val text = ByteArray(30) { (0x80 + it).toByte() }
        System.arraycopy(text, 0, frame1, 1000, text.size)

        val tmp = Files.createTempDirectory("moneo-cap").toFile()
        try {
            // Drive the capture by directly invoking the private path through
            // setEnabled + a tiny stubbed reader. Use reflection-free approach:
            // call setEnabled, then call the public sample loop one step at a
            // time by toggling the flag.
            val reader = FakeReader(listOf(frame0, frame1, frame1))
            val cap = RamCapture(reader, tmp)
            // Enable, wait briefly, disable. Simpler: invoke the package-private
            // sampleOnce via two toggles + a manual delay isn't deterministic.
            // Instead, exercise via the file: enable, wait until at least one
            // record is captured (or 2s timeout), then assert.
            cap.setEnabled(true)
            val deadline = System.currentTimeMillis() + 5_000
            while (cap.runsCaptured.value == 0 && System.currentTimeMillis() < deadline) {
                Thread.sleep(50)
            }
            cap.setEnabled(false)
            assertTrue("Expected at least one captured run", cap.runsCaptured.value >= 1)
            assertTrue("Capture file should exist", cap.captureFile().exists())
            assertTrue("Capture file should have content", cap.captureFile().length() > 4)
        } finally {
            tmp.deleteRecursively()
        }
    }
}
