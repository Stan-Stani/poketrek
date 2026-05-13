package com.poketrek.moneo.data

import android.content.Context
import org.json.JSONObject

/**
 * Loads bundled vocabulary entries from `assets/moneo/seed-vocab-ko.json`.
 * The JSON shape:
 * ```
 * {
 *   "version": 1,
 *   "sourceTag": "seed-v1",
 *   "entries": [
 *     { "korean": "포켓몬", "romanization": "pokemon", "gloss": "Pokémon",
 *       "partOfSpeech": "noun", "areaId": "pallet_town" },
 *     ...
 *   ]
 * }
 * ```
 *
 * Stable [VocabEntry.id] is composed as `"<sourceTag>:<korean>"` so subsequent
 * seed revisions don't churn the store and player progress is preserved across
 * upgrades.
 */
object SeedLoader {

    fun loadFromAssets(context: Context, path: String = "moneo/seed-vocab-ko.json"): List<VocabEntry> {
        val json = context.assets.open(path).use { it.readBytes() }.toString(Charsets.UTF_8)
        return parse(json)
    }

    fun parse(json: String): List<VocabEntry> {
        val root = JSONObject(json)
        val sourceTag = root.optString("sourceTag", "seed")
        val arr = root.getJSONArray("entries")
        val out = ArrayList<VocabEntry>(arr.length())
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            val korean = o.getString("korean")
            val areasRefArr = o.optJSONArray("areasReferenced")
            val areasReferenced: List<String> = if (areasRefArr != null) {
                buildList(areasRefArr.length()) {
                    for (j in 0 until areasRefArr.length()) {
                        val a = areasRefArr.optString(j)
                        if (a.isNotEmpty()) add(a)
                    }
                }
            } else emptyList()
            val sensesArr = o.optJSONArray("senses")
            val senses: List<String> = if (sensesArr != null) {
                buildList(sensesArr.length()) {
                    for (j in 0 until sensesArr.length()) {
                        val s = sensesArr.optString(j)
                        if (s.isNotEmpty()) add(s)
                    }
                }
            } else emptyList()
            out += VocabEntry(
                id = "$sourceTag:$korean",
                korean = korean,
                gloss = o.getString("gloss"),
                senses = senses,
                partOfSpeech = o.getString("partOfSpeech"),
                // Prefer firstAreaEncountered (set by the attribution
                // pipeline) so per-area review queues include species/mined/
                // topik cards whose generic areaId bucket is "rom_mined" /
                // "topik_1" while their actual in-game area is more specific.
                areaId = o.optString("firstAreaEncountered").takeIf { it.isNotEmpty() }
                    ?: o.getString("areaId"),
                sourceTag = sourceTag,
                notes = o.optString("notes").takeIf { it.isNotEmpty() },
                areasReferenced = areasReferenced,
                primarySourceType = o.optString("primarySourceType").takeIf { it.isNotEmpty() },
            )
        }
        return out
    }
}
