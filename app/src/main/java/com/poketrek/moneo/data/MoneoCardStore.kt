package com.poketrek.moneo.data

import android.content.Context
import android.util.Log
import com.poketrek.moneo.srs.CardSnapshot
import com.poketrek.moneo.srs.CardState
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.concurrent.atomic.AtomicReference

/**
 * Lightweight on-disk persistence for SRS card state. Keeps everything in
 * a single JSON file under `filesDir/moneo/cards.json`. Writes are debounced
 * via in-memory cache + atomic file replace; suitable for the MVP's expected
 * scale (hundreds of cards, not tens of thousands). When/if the corpus
 * grows past that, swap this for Room without touching callers — see
 * [MoneoRepository] for the seam.
 *
 * Thread-safe: read/write methods synchronize on the cache reference.
 */
class MoneoCardStore(private val rootDir: File) {

    private val file: File = File(rootDir, FILE_NAME)
    private val cache: AtomicReference<MutableMap<String, CardRecord>> = AtomicReference()

    private fun ensureLoaded(): MutableMap<String, CardRecord> {
        cache.get()?.let { return it }
        synchronized(this) {
            cache.get()?.let { return it }
            val loaded = if (file.exists()) {
                runCatching { read(file) }.getOrElse {
                    Log.w(TAG, "Failed to read $file; starting fresh", it)
                    linkedMapOf()
                }
            } else {
                linkedMapOf()
            }
            cache.set(loaded)
            return loaded
        }
    }

    fun all(): List<CardRecord> = synchronized(this) { ensureLoaded().values.toList() }

    fun get(vocabId: String): CardRecord? = synchronized(this) { ensureLoaded()[vocabId] }

    /** Insert if missing; preserves existing card state. */
    fun ensureExists(vocabIds: Collection<String>, now: Long) {
        synchronized(this) {
            val map = ensureLoaded()
            var changed = false
            for (id in vocabIds) {
                if (map[id] == null) {
                    map[id] = CardRecord(id, CardSnapshot(), now, null)
                    changed = true
                }
            }
            if (changed) writeLocked(map)
        }
    }

    fun put(record: CardRecord) {
        synchronized(this) {
            val map = ensureLoaded()
            map[record.vocabId] = record
            writeLocked(map)
        }
    }

    /** Remove all cards. Used by debug "reset Moneo" action. */
    fun clear() {
        synchronized(this) {
            cache.set(linkedMapOf())
            if (file.exists()) file.delete()
        }
    }

    private fun writeLocked(map: Map<String, CardRecord>) {
        rootDir.mkdirs()
        val tmp = File(rootDir, "$FILE_NAME.tmp")
        tmp.writeText(serialize(map))
        if (!tmp.renameTo(file)) {
            // Fall back to copy+delete if rename fails (e.g. across mount points).
            file.writeText(tmp.readText())
            tmp.delete()
        }
    }

    private fun serialize(map: Map<String, CardRecord>): String {
        val arr = JSONArray()
        for (rec in map.values) {
            val s = rec.snapshot
            val o = JSONObject()
            o.put("id", rec.vocabId)
            o.put("createdAt", rec.createdAt)
            rec.lastReviewedAt?.let { o.put("lastReviewedAt", it) }
            o.put("state", s.state.name)
            o.put("dueAt", s.dueAt)
            o.put("intervalDays", s.intervalDays)
            o.put("ease", s.ease)
            o.put("reps", s.reps)
            o.put("lapses", s.lapses)
            o.put("learningStep", s.learningStep)
            arr.put(o)
        }
        return JSONObject().apply {
            put("version", VERSION)
            put("cards", arr)
        }.toString()
    }

    private fun read(f: File): MutableMap<String, CardRecord> {
        val root = JSONObject(f.readText())
        val arr = root.optJSONArray("cards") ?: return linkedMapOf()
        val out = LinkedHashMap<String, CardRecord>(arr.length())
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            val id = o.getString("id")
            val snap = CardSnapshot(
                state = CardState.valueOf(o.optString("state", "NEW")),
                dueAt = o.optLong("dueAt", 0L),
                intervalDays = o.optDouble("intervalDays", 0.0),
                ease = o.optDouble("ease", CardSnapshot.STARTING_EASE),
                reps = o.optInt("reps", 0),
                lapses = o.optInt("lapses", 0),
                learningStep = o.optInt("learningStep", 0),
            )
            out[id] = CardRecord(
                vocabId = id,
                snapshot = snap,
                createdAt = o.optLong("createdAt", 0L),
                lastReviewedAt = if (o.has("lastReviewedAt")) o.getLong("lastReviewedAt") else null,
            )
        }
        return out
    }

    companion object {
        private const val TAG = "MoneoCardStore"
        private const val FILE_NAME = "cards.json"
        private const val VERSION = 1

        fun forContext(context: Context): MoneoCardStore =
            MoneoCardStore(File(context.filesDir, "moneo"))
    }
}
