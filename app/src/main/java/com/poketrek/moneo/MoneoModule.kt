package com.poketrek.moneo

import android.content.Context
import com.poketrek.moneo.corpus.RamCapture
import com.poketrek.moneo.data.AreaCatalog
import com.poketrek.moneo.data.MoneoCardStore
import com.poketrek.moneo.data.MoneoPrefs
import com.poketrek.moneo.data.MoneoRepository
import com.poketrek.moneo.data.SeedLoader
import java.io.File

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
        val vocabSeed = runCatching { SeedLoader.loadFromAssets(context) }.getOrElse { emptyList() }
        // Auto-mined vocab from corpus.ko.json. Optional — if the file is
        // absent or fails to parse, fall back to seed-only.
        val vocabMined = runCatching {
            SeedLoader.loadFromAssets(context, "moneo/seed-vocab-ko-mined.json")
        }.getOrElse { emptyList() }
        val vocab = vocabSeed + vocabMined
        val sentencesRom = runCatching {
            com.poketrek.moneo.data.SentenceLoader.loadFromAssets(context, "moneo/sentences-ko-rom.json")
        }.getOrElse { emptyList() }
        val sentencesStudy = runCatching {
            com.poketrek.moneo.data.SentenceLoader.loadFromAssets(context, "moneo/sentences-ko-study.json")
        }.getOrElse { emptyList() }
        // Mined sentences are used regardless of the verbatim toggle (they're
        // the only source for mined vocab, and they're always ROM-sourced).
        val sentencesMined = runCatching {
            com.poketrek.moneo.data.SentenceLoader.loadFromAssets(context, "moneo/sentences-ko-mined.json")
        }.getOrElse { emptyList() }
        repository = MoneoRepository(
            store = store,
            initialVocab = vocab,
            initialAreas = areas,
            initialSentencesRom = sentencesRom + sentencesMined,
            initialSentencesStudy = sentencesStudy + sentencesMined,
        )
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
