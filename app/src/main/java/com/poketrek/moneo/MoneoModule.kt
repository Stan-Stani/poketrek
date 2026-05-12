package com.poketrek.moneo

import android.content.Context
import com.poketrek.moneo.corpus.RamCapture
import com.poketrek.moneo.data.AreaCatalog
import com.poketrek.moneo.data.MoneoCardStore
import com.poketrek.moneo.data.MoneoPrefs
import com.poketrek.moneo.data.MoneoRepository
import com.poketrek.moneo.data.SeedLoader
import java.io.File
import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.launch

/**
 * Process-wide singleton owning Moneo's collaborators. Mirrors the
 * `MovementBudget.get(context)` pattern so we stay dependency-injection-free.
 *
 * Intentional rule: nothing in `com.poketrek.moneo.*` may import anything
 * from `com.poketrek.step.*`. The two features share only the `EmulatorActivity`
 * + `EmulatorScreen` mount points.
 */
class MoneoModule private constructor(context: Context) {
    val prefs: MoneoPrefs = MoneoPrefs.get(context)
    val repository: MoneoRepository
    /** Korean TTS engine for the example-sentence speaker button. Lazily
     *  initialized so process startup doesn't pay for TextToSpeech bind
     *  unless the user actually opens the review screen. */
    val tts: com.poketrek.moneo.audio.TtsPlayer by lazy {
        com.poketrek.moneo.audio.TtsPlayer(context.applicationContext)
    }
    private val captureDir: File = File(context.filesDir, "moneo")

    /**
     * Lazily-attached runtime EWRAM capture. Built on demand once the
     * runner is constructed; call [bindCapture] from the activity.
     * Null until bound; callers should null-check.
     */
    @Volatile var ramCapture: RamCapture? = null
        private set

    init {
        val store = MoneoCardStore.forContext(context)
        val areas = runCatching { AreaCatalog.loadFromAssets(context) }.getOrElse { emptyList() }
        // seed-vocab-ko.json retired 2026-05-12 — its 45 entries were
        // hand-curated MVP placeholders, now migrated into seed-vocab-
        // ko-mined.json with rom-mine-v2 ids. SeedLoader is still used
        // for the larger mined/topik/species/etymology decks below.
        val vocabSeed = emptyList<com.poketrek.moneo.data.VocabEntry>()
        // Auto-mined vocab from corpus.ko.json. Optional — if the file is
        // absent or fails to parse, fall back to seed-only.
        val vocabMined = runCatching {
            SeedLoader.loadFromAssets(context, "moneo/seed-vocab-ko-mined.json")
        }.getOrElse { emptyList() }
        // TOPIK 1+2 vocab that also occurs in the ROM corpus (~700 cards,
        // hand-glossed). Optional like the mined deck.
        val vocabTopik = runCatching {
            SeedLoader.loadFromAssets(context, "moneo/seed-vocab-ko-topik.json")
        }.getOrElse { emptyList() }
        // Species names (proper nouns) extracted from gSpeciesNames in the
        // 2024 ROM. Always loaded; runtime filtering driven by
        // prefs.includeSpecies via repository.setExcludedSourceTags below.
        val vocabSpecies = runCatching {
            SeedLoader.loadFromAssets(context, "moneo/seed-vocab-ko-species.json")
        }.getOrElse { emptyList() }
        // Korean root morphemes harvested from species-name pun etymologies.
        // Off by default; opt-in via prefs.includeEtymology.
        val vocabEtymology = runCatching {
            SeedLoader.loadFromAssets(context, "moneo/seed-vocab-ko-etymology.json")
        }.getOrElse { emptyList() }
        val vocab = vocabSeed + vocabMined + vocabTopik + vocabSpecies + vocabEtymology
        val sentencesRom = runCatching {
            com.poketrek.moneo.data.SentenceLoader.loadFromAssets(context, "moneo/sentences-ko-rom.json")
        }.getOrElse { emptyList() }
        val sentencesStudy = runCatching {
            com.poketrek.moneo.data.SentenceLoader.loadFromAssets(context, "moneo/sentences-ko-study.json")
        }.getOrElse { emptyList() }
        // Mined sentences are ROM-sourced — only included in the verbatim
        // (spoiler-on) corpus. Mined vocab cards therefore have no example
        // sentence when the user has spoilers off.
        val sentencesMined = runCatching {
            com.poketrek.moneo.data.SentenceLoader.loadFromAssets(context, "moneo/sentences-ko-mined.json")
        }.getOrElse { emptyList() }
        val sentencesTopik = runCatching {
            com.poketrek.moneo.data.SentenceLoader.loadFromAssets(context, "moneo/sentences-ko-topik.json")
        }.getOrElse { emptyList() }
        // Species sentences match the species vocab deck. Same shape as the
        // other corpora; auto-generated example sentences.
        val sentencesSpecies = runCatching {
            com.poketrek.moneo.data.SentenceLoader.loadFromAssets(context, "moneo/sentences-ko-species.json")
        }.getOrElse { emptyList() }
        val sentencesEtymology = runCatching {
            com.poketrek.moneo.data.SentenceLoader.loadFromAssets(context, "moneo/sentences-ko-etymology.json")
        }.getOrElse { emptyList() }
        // Hand-curated themed sentences for vocab whose only sentence sources
        // are ROM-derived. Joins the spoiler-free corpus so mined/topik/
        // species/etymology cards still get an example when verbatim is off.
        val sentencesThemed = runCatching {
            com.poketrek.moneo.data.SentenceLoader.loadFromAssets(context, "moneo/sentences-ko-themed.json")
        }.getOrElse { emptyList() }
        // LLM-generated themed sentences for the species deck (241 of 246;
        // the other 5 starters live in sentences-ko-themed.json as the
        // hand-reviewed voice reference). Replaces the templated "야생의 X
        // 가 나타났다!" lines whenever verbatim is off.
        val sentencesThemedSpecies = runCatching {
            com.poketrek.moneo.data.SentenceLoader.loadFromAssets(context, "moneo/sentences-ko-themed-species.json")
        }.getOrElse { emptyList() }
        // LLM-generated themed sentences for the mined deck (586 of 591;
        // 5 lemmas already in sentences-ko-themed.json). Replaces the
        // rotated-ROM placeholders in the no-spoiler corpus.
        val sentencesThemedMined = runCatching {
            com.poketrek.moneo.data.SentenceLoader.loadFromAssets(context, "moneo/sentences-ko-themed-mined.json")
        }.getOrElse { emptyList() }
        // LLM-generated themed sentences for the TOPIK 1+2 deck (708 of
        // 713; 5 lemmas already in sentences-ko-themed.json). Voice is
        // looser than the mined deck — TOPIK includes general everyday
        // vocab (food/weather/family) so not every sentence is Pokémon-
        // flavored.
        val sentencesThemedTopik = runCatching {
            com.poketrek.moneo.data.SentenceLoader.loadFromAssets(context, "moneo/sentences-ko-themed-topik.json")
        }.getOrElse { emptyList() }
        val allRomSentences = sentencesRom + sentencesMined + sentencesTopik + sentencesSpecies + sentencesEtymology
        // Spoiler-free corpus: hand-curated study sentences plus the themed
        // batch. The mined/topik/species/etymology corpora themselves are all
        // ROM-sourced (or surface in-game species names) so they leak content
        // when the user explicitly opts out of spoilers via the verbatim toggle.
        val allStudySentences = sentencesStudy + sentencesThemed + sentencesThemedSpecies + sentencesThemedMined + sentencesThemedTopik
        repository = MoneoRepository(
            store = store,
            initialVocab = vocab,
            initialAreas = areas,
            initialSentencesRom = allRomSentences,
            initialSentencesStudy = allStudySentences,
        )
        // Drive optional-deck visibility from user prefs. Combined so toggles
        // take effect immediately without an app restart.
        GlobalScope.launch {
            kotlinx.coroutines.flow.combine(prefs.includeSpecies, prefs.includeEtymology) { species, etym ->
                val tags = mutableSetOf<String>()
                if (!species) tags.add("rom-species-2024")
                if (!etym) tags.add("etymology-roots")
                tags.toSet()
            }.collect { repository.setExcludedSourceTags(it) }
        }
    }

    /** Wire up the optional runtime EWRAM capture once the runner exists. */
    fun bindCapture(reader: RamCapture.BusReader) {
        if (ramCapture == null) {
            ramCapture = RamCapture(reader, captureDir)
        }
    }

    companion object {
        @Volatile private var instance: MoneoModule? = null
        fun get(context: Context): MoneoModule = instance ?: synchronized(this) {
            instance ?: MoneoModule(context.applicationContext).also { instance = it }
        }
    }
}
