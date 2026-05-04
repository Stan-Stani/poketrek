package com.poketrek.moneo.corpus

import android.util.Log

/**
 * Decodes Korean text currently visible on-screen by scanning VRAM.
 *
 * The Korean LeafGreen ROM renders dialog text on a BG layer configured as:
 *   charbase = 0  (glyph pixel data at VRAM 0x06000000)
 *   screenbase = 31  (tile-index map at VRAM 0x0600F800)
 *
 * Each Hangul character occupies a 2×2 tile block (16×16 px). The dialog box
 * can hold 11 characters per line across 7 line-pairs in the visible area.
 *
 * Usage:
 * ```kotlin
 * val charmap = KoreanCharmap.get(context)
 * val lines   = VramTextReader.readLines(busReader, charmap)
 * ```
 */
object VramTextReader {

    private const val TAG = "VramTextReader"

    // GBA VRAM layout constants
    private const val VRAM_BASE = 0x06000000
    private const val VRAM_BG_BYTES = 65536          // 64 KB covers all 4 charbases + all 32 SBs
    private const val SB31_OFFSET = 31 * 2048        // 0xF800 — text tile-index map
    private const val MAP_COLS = 32                  // tile columns per screenblock row
    private const val CHARS_PER_LINE = 11

    /**
     * Top tile-row indices (in SB31 coordinates) for each text line-pair.
     * Each pair is (topRow, topRow+1); both rows together make one character line.
     */
    private val TEXT_ROW_TOPS = intArrayOf(3, 5, 7, 10, 12, 15, 17)

    /**
     * Read and decode all Korean text currently visible on-screen.
     *
     * Returns a list of non-blank decoded lines. Each line is at most 11
     * characters (spaces used for empty slots). Returns an empty list when
     * the bus read fails or no text tile-map entries are present.
     */
    fun readLines(reader: RamCapture.BusReader, charmap: KoreanCharmap): List<String> {
        val vram = reader.readBytes(VRAM_BASE, VRAM_BG_BYTES) ?: return emptyList()
        if (vram.size < VRAM_BG_BYTES) return emptyList()

        val lines = mutableListOf<String>()
        for (topRow in TEXT_ROW_TOPS) {
            val line = decodeLine(vram, topRow, charmap)
            if (line.isNotBlank()) lines += line
        }

        if (lines.isNotEmpty()) {
            Log.d(TAG, "Decoded ${lines.size} lines: ${lines.joinToString(" / ")}")
        }
        return lines
    }

    private fun decodeLine(vram: ByteArray, topRow: Int, charmap: KoreanCharmap): String {
        val startCol = findStartCol(vram, topRow) ?: return ""

        return buildString {
            for (n in 0 until CHARS_PER_LINE) {
                val col = startCol + n * 2
                if (col + 1 >= MAP_COLS) break

                val tl = sb31Tile(vram, topRow,     col)
                val tr = sb31Tile(vram, topRow,     col + 1)
                val bl = sb31Tile(vram, topRow + 1, col)
                val br = sb31Tile(vram, topRow + 1, col + 1)

                if (tl == 0 && tr == 0 && bl == 0 && br == 0) {
                    append(' ')
                } else {
                    append(charmap.decode(vram, tl, tr, bl, br) ?: '?')
                }
            }
        }.trimEnd()
    }

    /** Find the first column in [row] of SB31 that has a non-zero tile index. */
    private fun findStartCol(vram: ByteArray, row: Int): Int? {
        for (col in 0 until MAP_COLS) {
            if (sb31Tile(vram, row, col) != 0) return col
        }
        return null
    }

    /** Read one 10-bit tile index from SB31 at (row, col). Little-endian 2-byte entry. */
    private fun sb31Tile(vram: ByteArray, row: Int, col: Int): Int {
        val offset = SB31_OFFSET + (row * MAP_COLS + col) * 2
        if (offset + 2 > vram.size) return 0
        return ((vram[offset].toInt() and 0xFF) or
                ((vram[offset + 1].toInt() and 0xFF) shl 8)) and 0x3FF
    }
}
