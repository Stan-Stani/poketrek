package com.poketrek.moneo.data

import android.content.Context
import org.json.JSONObject

/**
 * One in-game area unit for vocab grouping and area-gating. Loaded from
 * `assets/moneo/areas.json`; ordered by [ordinal] which determines the
 * area-picker layout and (later) hard-gate progression.
 */
data class Area(
    val id: String,
    val englishName: String,
    val koreanLabel: String,
    val ordinal: Int,
)

object AreaCatalog {

    fun loadFromAssets(context: Context, path: String = "moneo/areas.json"): List<Area> {
        val json = context.assets.open(path).use { it.readBytes() }.toString(Charsets.UTF_8)
        return parse(json)
    }

    fun parse(json: String): List<Area> {
        val root = JSONObject(json)
        val arr = root.getJSONArray("areas")
        val out = ArrayList<Area>(arr.length())
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            out += Area(
                id = o.getString("id"),
                englishName = o.getString("englishName"),
                koreanLabel = o.getString("koreanLabel"),
                ordinal = o.getInt("ordinal"),
            )
        }
        return out.sortedBy { it.ordinal }
    }
}
