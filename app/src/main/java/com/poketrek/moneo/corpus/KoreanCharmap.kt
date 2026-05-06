package com.poketrek.moneo.corpus

import android.content.Context
import android.util.Log
import org.json.JSONObject
import java.security.MessageDigest

/**
 * Maps pixel fingerprints of GBA 2×2 tile groups to Korean Unicode characters.
 *
 * Each Hangul character in the Korean LeafGreen ROM occupies a 2×2 tile block
 * (top-left, top-right, bottom-left, bottom-right tiles). A SHA-256 prefix of
 * the concatenated 128 bytes (4 × 32-byte 4bpp tiles) uniquely identifies the
 * rendered glyph.
 *
 * The table is loaded once from `assets/moneo/ko_charmap.json`, which was
 * derived offline by cross-referencing known tutorial-page text with VRAM
 * pixel captures. The file maps 16-char hex fingerprint → single Korean char.
 *
 * At runtime all four GBA BG charbases (0-3) are tried for each tile group
 * because the active charbase can vary by game state (tutorial vs dialog box).
 */
class KoreanCharmap private constructor(
    private val fpToChar: Map<String, String>,
) {

    /**
     * Decode one Korean character from a 64 KB VRAM snapshot.
     *
     * @param vram64k 64 KB read of VRAM starting at 0x06000000.
     * @param tl      Top-left tile index (from SB31 tile map).
     * @param tr      Top-right tile index.
     * @param bl      Bottom-left tile index.
     * @param br      Bottom-right tile index.
     * @return Unicode Korean character, or null if unrecognised.
     */
    fun decode(vram64k: ByteArray, tl: Int, tr: Int, bl: Int, br: Int): String? {
        if (vram64k.size < VRAM_BG_SIZE) return null
        val raw = ByteArray(128)
        for (cb in 0 until 4) {
            val base = cb * CHARBLOCK_SIZE
            for ((i, idx) in intArrayOf(tl, tr, bl, br).withIndex()) {
                val off = base + idx * TILE_BYTES
                if (off + TILE_BYTES <= VRAM_BG_SIZE) {
                    vram64k.copyInto(raw, i * TILE_BYTES, off, off + TILE_BYTES)
                } else {
                    raw.fill(0, i * TILE_BYTES, (i + 1) * TILE_BYTES)
                }
            }
            val fp = sha256hex16(raw)
            fpToChar[fp]?.let { return it }
        }
        return null
    }

    /** Number of entries in the charmap (useful for diagnostics). */
    val size: Int get() = fpToChar.size

    private fun sha256hex16(data: ByteArray): String {
        val digest = MessageDigest.getInstance("SHA-256").digest(data)
        return buildString(16) {
            for (i in 0 until 8) {
                append(HEX[(digest[i].toInt() ushr 4) and 0xF])
                append(HEX[digest[i].toInt() and 0xF])
            }
        }
    }

    companion object {
        private const val TAG = "KoreanCharmap"
        private const val ASSET_PATH = "moneo/ko_charmap.json"
        private val HEX = "0123456789abcdef".toCharArray()

        private const val VRAM_BG_SIZE = 65536   // 64 KB total BG VRAM
        private const val CHARBLOCK_SIZE = 16384  // 16 KB per charblock (SBs × 8)
        private const val TILE_BYTES = 32         // 4bpp 8×8 tile = 32 bytes

        @Volatile private var instance: KoreanCharmap? = null

        fun get(context: Context): KoreanCharmap =
            instance ?: synchronized(this) {
                instance ?: load(context).also { instance = it }
            }

        private fun load(context: Context): KoreanCharmap {
            return try {
                val text = context.assets.open(ASSET_PATH).bufferedReader().use { it.readText() }
                val obj = JSONObject(text)
                val map = HashMap<String, String>(obj.length() * 2)
                for (fp in obj.keys()) map[fp] = obj.getString(fp)
                Log.i(TAG, "Loaded ${map.size} Korean char fingerprints")
                KoreanCharmap(map)
            } catch (e: Exception) {
                Log.e(TAG, "Failed to load $ASSET_PATH", e)
                KoreanCharmap(emptyMap())
            }
        }
    }
}
