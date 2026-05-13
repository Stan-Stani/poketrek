package com.poketrek.moneo.correction

import org.json.JSONObject

/**
 * One user-submitted correction proposal for a moneo sentence.
 *
 * Designed so a maintainer can act on the report without round-tripping
 * with the reporter — every field they'd need to find and fix the sentence
 * in the bundled corpus is included. The receiving side (GitHub Issue or
 * the user's VPS) consumes the same shape.
 *
 * There's no globally-stable sentence ID in the bundled JSON files, so
 * we identify the affected sentence by the (vocabId, currentKorean) pair
 * which is unique within the corpus per `SentenceCorpusTest` invariants.
 */
data class CorrectionReport(
    /** From `SentenceEntry.vocabId` — links to the headword being studied. */
    val vocabId: String,
    /** Human-readable headword (e.g. "포켓몬") for display + grep. */
    val vocabHeadword: String,
    /** Headword English gloss (e.g. "Pokémon"). */
    val vocabGloss: String,
    /** Area context (e.g. "pallet_town"); null for area-agnostic sentences. */
    val areaId: String?,
    /** The Korean text the user is reporting as wrong. */
    val currentKorean: String,
    /** The English gloss currently shipped alongside the Korean. */
    val currentGloss: String,
    /** From `SentenceEntry.source` — e.g. "rom-rec1344" for ROM-extracted lines. */
    val source: String?,
    /** From `SentenceEntry.speaker` — named NPC if any (e.g. "오키드"). */
    val speaker: String?,
    /**
     * From `SentenceEntry.generator`. Tells the maintainer whether the line
     * came out of an LLM ("llm-<model>"), was hand-written ("human"), or is
     * a verbatim ROM rip (null). Routes triage: LLM corrections are usually
     * grammar/translation, ROM corrections might be character-mapping bugs.
     */
    val generator: String?,
    /** User's proposed replacement Korean. Null when the user is just flagging. */
    val proposedKorean: String?,
    /**
     * User's proposed replacement English gloss (or sentence translation
     * when reporting on a sentence). Null when unchanged. Either side may
     * be edited in a single report — the maintainer reads which one
     * differs from the corresponding `current*` field to triage as
     * `ko-fix` or `en-fix`.
     */
    val proposedGloss: String?,
    /** Free-text "why is this wrong" explanation. Optional. */
    val reason: String?,
    /** App build for context. */
    val appVersion: String,
    /** ROM CRC32 hex (e.g. "0xDAFFECEC") so we know which variant the user saw. */
    val romCrc32: String?,
) {
    fun toJson(): String = JSONObject().apply {
        put("vocab_id", vocabId)
        put("vocab_headword", vocabHeadword)
        put("vocab_gloss", vocabGloss)
        put("area_id", areaId ?: JSONObject.NULL)
        put("current_korean", currentKorean)
        put("current_gloss", currentGloss)
        put("source", source ?: JSONObject.NULL)
        put("speaker", speaker ?: JSONObject.NULL)
        put("generator", generator ?: JSONObject.NULL)
        put("proposed_korean", proposedKorean ?: JSONObject.NULL)
        put("proposed_gloss", proposedGloss ?: JSONObject.NULL)
        put("reason", reason ?: JSONObject.NULL)
        put("app_version", appVersion)
        put("rom_crc32", romCrc32 ?: JSONObject.NULL)
    }.toString()
}
