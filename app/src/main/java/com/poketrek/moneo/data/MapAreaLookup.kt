package com.poketrek.moneo.data

import android.content.Context
import org.json.JSONObject

/**
 * Runtime lookup from in-game `(mapBank, mapId)` (the bytes the player struct
 * exposes via `LeafGreenRam.Snapshot`) to a Moneo `Area.id`. The data is built
 * by `tools/moneo/resolve_map_areas.py` from the pokefirered map tables and
 * shipped as `assets/moneo/map_to_area.json`.
 *
 * Returns null for maps with no resolved area (e.g. cutscene-only maps the
 * player can't normally reach).
 */
class MapAreaLookup(private val byBankAndId: Map<Long, String>) {

    /** Compose a stable key so we can use a primitive map. */
    private fun key(mapBank: Int, mapId: Int): Long =
        (mapBank.toLong() and 0xFF) shl 8 or (mapId.toLong() and 0xFF)

    fun areaIdFor(mapBank: Int, mapId: Int): String? = byBankAndId[key(mapBank, mapId)]

    companion object {
        fun parse(json: String): MapAreaLookup {
            val root = JSONObject(json)
            val maps = root.getJSONObject("maps")
            val out = HashMap<Long, String>(maps.length())
            val keys = maps.keys()
            while (keys.hasNext()) {
                val k = keys.next()
                val parts = k.split(":")
                if (parts.size != 2) continue
                val bank = parts[0].toIntOrNull() ?: continue
                val id = parts[1].toIntOrNull() ?: continue
                val areaId = maps.optString(k).takeIf { it.isNotBlank() } ?: continue
                out[(bank.toLong() and 0xFF) shl 8 or (id.toLong() and 0xFF)] = areaId
            }
            return MapAreaLookup(out)
        }

        fun loadFromAssets(
            context: Context,
            path: String = "moneo/map_to_area.json",
        ): MapAreaLookup {
            val json = context.assets.open(path).use { it.readBytes() }.toString(Charsets.UTF_8)
            return parse(json)
        }
    }
}
