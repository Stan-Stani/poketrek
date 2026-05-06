package com.poketrek.moneo.corpus

import java.io.File
import java.io.RandomAccessFile

/**
 * Reader for the binary capture format written by [RamCapture].
 *
 * File layout (little-endian, single header followed by N records):
 *   magic = 'KCAP' (4 bytes)
 *   record* :
 *     u32 timestamp_ms_low
 *     u32 addr
 *     u32 length
 *     u32 crc32
 *     u8[length] bytes
 *
 * Pure JVM — runnable as a host-side dev tool to inspect capture files
 * pulled off the device via `adb pull`.
 */
object CaptureReader {

    data class Record(
        val timestampMs: Int,
        val addr: Int,
        val crc32: Long,
        val bytes: ByteArray,
    )

    fun read(file: File): List<Record> {
        if (!file.exists() || file.length() < 4) return emptyList()
        RandomAccessFile(file, "r").use { f ->
            val magic = ByteArray(4).also { f.readFully(it) }
            if (!(magic[0] == 'K'.code.toByte() && magic[1] == 'C'.code.toByte() &&
                  magic[2] == 'A'.code.toByte() && magic[3] == 'P'.code.toByte())) {
                error("Bad magic: ${magic.joinToString("") { "%02x".format(it) }}")
            }
            val out = ArrayList<Record>()
            while (f.filePointer < f.length()) {
                val ts = readLeI32(f)
                val addr = readLeI32(f)
                val len = readLeI32(f)
                val crc = readLeI32(f).toLong() and 0xFFFFFFFFL
                if (len < 0 || len > 1 shl 20) error("Bogus length $len at offset ${f.filePointer}")
                val bytes = ByteArray(len).also { f.readFully(it) }
                out += Record(ts, addr, crc, bytes)
            }
            return out
        }
    }

    private fun readLeI32(f: RandomAccessFile): Int {
        val b0 = f.read(); val b1 = f.read(); val b2 = f.read(); val b3 = f.read()
        if (b3 < 0) error("Truncated record")
        return (b0 and 0xFF) or
               ((b1 and 0xFF) shl 8) or
               ((b2 and 0xFF) shl 16) or
               ((b3 and 0xFF) shl 24)
    }
}
