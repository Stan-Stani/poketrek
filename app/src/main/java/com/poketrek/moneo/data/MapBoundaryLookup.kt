package com.poketrek.moneo.data

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/**
 * Boundary tile that connects to another area (edge or warp).
 * For edge tiles, `dir` indicates which direction the player must press
 * to trigger the transition (e.g. "up" for the top edge of a route).
 * For warp tiles, `dir` is `null` and the transition happens regardless
 * of the direction the player is pressing.
 */
data class Boundary(
    val x: Int,
    val y: Int,
    val dir: String?,
    val destBank: Int,
    val destMapId: Int,
    val destArea: String,
    val kind: String // "edge" or "warp"
)

/**
 * Runtime lookup of map boundaries shipped as `assets/moneo/boundary_tiles.json`.
 *
 * Each map (identified by `bank:mapId`) has a list of [Boundary] entries
 * that lead to another area. The file is built by the tooling and uses
 * the Moneo area id as the destination.
 */
class MapBoundaryLookup(private val byMap: Map<Long, List<Boundary>>) {

    /** Compose a stable key from bank and mapId. */
    private fun mapKey(bank: Int, mapId: Int): Long =
        (bank.toLong() and 0xFF) shl 8 or (mapId.toLong() and 0xFF)

    /**
     * Returns all boundaries defined for the given map.
     * An empty list is returned when the map has no boundary data.
     */
    fun boundariesFor(bank: Int, mapId: Int): List<Boundary> =
        byMap[mapKey(bank, mapId)] ?: emptyList()

    /**
     * Returns the first boundary at tile ([x], [y]) that should trigger
     * given the [pressedDir] (the direction the player is pressing, or null
     * if no directional input is active).
     *
     * Edge boundaries only match when [pressedDir] equals the boundary's
     * direction. Warp boundaries match regardless of [pressedDir].
     *
     * Returns null if no matching boundary exists.
     */
    fun boundaryAt(bank: Int, mapId: Int, x: Int, y: Int, pressedDir: String?): Boundary? {
        return boundariesFor(bank, mapId).firstOrNull { boundary ->
            boundary.x == x && boundary.y == y &&
                    (boundary.kind == "warp" || (boundary.kind == "edge" && pressedDir == boundary.dir))
        }
    }

    companion object {

        /**
         * Parses the JSON content of `boundary_tiles.json`.
         *
         * Malformed entries (e.g. missing fields, non-integer coordinates)
         * are silently skipped so the rest of the file still loads.
         */
        fun parse(json: String): MapBoundaryLookup {
            val root = JSONObject(json)
            val boundariesObj = root.getJSONObject("boundaries")
            val out = HashMap<Long, MutableList<Boundary>>()

            val keys = boundariesObj.keys()
            while (keys.hasNext()) {
                val mapKeyStr = keys.next()
                val parts = mapKeyStr.split(":")
                if (parts.size != 2) continue
                val bank = parts[0].toIntOrNull() ?: continue
                val mapId = parts[1].toIntOrNull() ?: continue

                val arr: JSONArray = boundariesObj.optJSONArray(mapKeyStr) ?: continue
                val list = out.getOrPut((bank.toLong() and 0xFF) shl 8 or (mapId.toLong() and 0xFF)) { mutableListOf() }

                for (i in 0 until arr.length()) {
                    val entry = arr.optJSONObject(i) ?: continue
                    val x = entry.optInt("x", Int.MIN_VALUE)
                    val y = entry.optInt("y", Int.MIN_VALUE)
                    if (x == Int.MIN_VALUE || y == Int.MIN_VALUE) continue

                    // For warps the JSON literal is `"dir": null`; org.json's
                    // optString returns "" in that case, which we map to null.
                    val dirRaw = if (entry.isNull("dir")) null else entry.optString("dir", "")
                    val dir = dirRaw?.takeIf { it.isNotBlank() }
                    // destBank and destMapId must be present; skip if missing
                    val destBank = entry.optInt("destBank", Int.MIN_VALUE)
                    if (destBank == Int.MIN_VALUE) continue
                    val destMapId = entry.optInt("destMapId", Int.MIN_VALUE)
                    if (destMapId == Int.MIN_VALUE) continue

                    val destArea = entry.optString("destArea", "").takeIf { it.isNotBlank() } ?: continue
                    val kind = entry.optString("kind", "").takeIf { it == "edge" || it == "warp" } ?: continue

                    list.add(Boundary(x, y, dir, destBank, destMapId, destArea, kind))
                }
            }

            // Convert mutable lists to immutable
            val immutableMap = out.mapValues { it.value.toList() }
            return MapBoundaryLookup(immutableMap)
        }

        /**
         * Loads boundary data from the app's assets.
         *
         * @param context Application context for asset access.
         * @param path Asset path (defaults to "moneo/boundary_tiles.json").
         */
        fun loadFromAssets(
            context: Context,
            path: String = "moneo/boundary_tiles.json"
        ): MapBoundaryLookup {
            val json = context.assets.open(path).use { it.readBytes() }.toString(Charsets.UTF_8)
            return parse(json)
        }
    }
}