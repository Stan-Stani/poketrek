package com.poketrek.moneo.data

import com.poketrek.moneo.srs.CardSnapshot

/**
 * One Korean vocabulary entry. Loaded from bundled JSON in `assets/moneo/`
 * at first launch and merged into the on-disk store. The seed file may be
 * extended over time; new entries are added without disturbing existing
 * card state (matched by [id]).
 */
data class VocabEntry(
    /** Stable id: `"<sourceTag>:<korean>"`. Survives across seed-file edits. */
    val id: String,
    val korean: String,
    /**
     * Primary English headword — one word or short phrase, no semicolons.
     * For ROM-table-anchored entries this is the canonical in-game English
     * extracted by `tools/moneo/build_name_table_decks_en.py` and pinned
     * into the asset by `restructure_glosses.py`.
     */
    val gloss: String,
    val partOfSpeech: String,
    /**
     * Primary area for this card — typically the area where the player first
     * encounters it (`firstAreaEncountered`) or, for hand-curated decks, the
     * `areaId` field. Used as the canonical "home area" for sorting.
     */
    val areaId: String,
    val sourceTag: String,
    val notes: String? = null,
    /**
     * Every canonical area where the lemma appears in ROM script/dialog.
     * Empty for hand-curated decks (use [areaId] alone). Populated by the
     * attribution pipeline (`tools/moneo/attribute_existing_decks.py`).
     * Repository queries broaden card visibility through this set so the
     * player sees a card in *every* area where it surfaces, not only the
     * first-encountered area.
     */
    val areasReferenced: List<String> = emptyList(),
    /**
     * Coarse provenance tag (e.g. `pokemon_move`, `pokemon_ability`,
     * `pokedex_entry`, `npc_dialog`, `system_text`, `item_description`,
     * `pokemon_species`). Used by the repository to opt out of, or split
     * out, specific kinds of cards into pseudo-areas. Null on decks that
     * don't carry the field.
     */
    val primarySourceType: String? = null,
    /**
     * Secondary senses surfaced under [gloss] on the card back. Populated
     * from semicolon-split manual glosses (for dialog lemmas) or from
     * `dialog_map_en.json` (curated overrides). Empty for most ROM-anchored
     * entries — one canonical name is unambiguous. Last in the parameter
     * list so existing positional callers stay source-compatible.
     */
    val senses: List<String> = emptyList(),
)

/**
 * Persistent SRS state for a single [VocabEntry]. Carries the SM-2
 * [CardSnapshot] plus identity + timestamps useful for the UI.
 */
data class CardRecord(
    val vocabId: String,
    val snapshot: CardSnapshot,
    val createdAt: Long,
    val lastReviewedAt: Long? = null,
    /**
     * User-suspended ("I know this") cards stay in storage but are hidden from
     * review queues and progress counts. Reversible via [MoneoRepository.setSuspended].
     */
    val suspended: Boolean = false,
)

data class AreaProgress(
    val areaId: String,
    val total: Int,
    val newCount: Int,
    val learningCount: Int,
    val reviewCount: Int,
    val dueCount: Int,
)
