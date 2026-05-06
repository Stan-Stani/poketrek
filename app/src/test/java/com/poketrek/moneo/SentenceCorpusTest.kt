package com.poketrek.moneo

import com.poketrek.moneo.data.SeedLoader
import com.poketrek.moneo.data.SentenceLoader
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * Build-time validator for the bundled sentence corpus.
 *
 * Runs as part of `./gradlew test`. Enforces:
 *   1. JSON parses cleanly.
 *   2. Every sentence's `vocabId` resolves to an existing seed entry.
 *   3. The sentence's `korean` string contains the target vocab's
 *      `korean` field as a substring (so the example actually exercises
 *      the word being learned).
 *   4. Romanization and gloss are non-blank.
 *   5. No duplicate `(vocabId, korean)` pairs.
 */
class SentenceCorpusTest {

    private val assetsDir = File("src/main/assets/moneo")

    @Test fun sentencesFileExists() {
        val f = File(assetsDir, "sentences-ko.json")
        assertTrue("sentences-ko.json must exist at ${f.absolutePath}", f.exists())
    }

    @Test fun everySentenceTargetsExistingVocab() {
        val (vocabIds, sentences) = load()
        val orphans = sentences.filter { it.vocabId !in vocabIds }
        assertTrue(
            "Sentences referencing unknown vocabIds: ${orphans.map { it.vocabId }}",
            orphans.isEmpty(),
        )
    }

    @Test fun everySentenceContainsTargetKoreanSubstring() {
        val seedJson = File(assetsDir, "seed-vocab-ko.json").readText()
        val vocab = SeedLoader.parse(seedJson).associateBy { it.id }
        val sentences = SentenceLoader.parse(
            File(assetsDir, "sentences-ko.json").readText()
        )
        val violations = sentences.mapNotNull { s ->
            val target = vocab[s.vocabId] ?: return@mapNotNull null
            // Override wins when present (irregular conjugations).
            val needle = s.targetForm
                ?: if (target.korean.length > 1 && target.korean.endsWith("다"))
                    target.korean.dropLast(1) else target.korean
            if (needle in s.korean) null else "${s.vocabId} (need '$needle' in '${s.korean}')"
        }
        assertTrue(
            "Sentences missing their target word as substring: $violations",
            violations.isEmpty(),
        )
    }

    @Test fun noBlankFields() {
        val (_, sentences) = load()
        val bad = sentences.filter {
            it.korean.isBlank() || it.romanization.isBlank() || it.gloss.isBlank()
        }
        assertTrue("Sentences with blank fields: ${bad.map { it.vocabId }}", bad.isEmpty())
    }

    @Test fun noDuplicatePairs() {
        val (_, sentences) = load()
        val keys = sentences.map { it.vocabId to it.korean }
        val dupes = keys.groupingBy { it }.eachCount().filter { it.value > 1 }.keys
        assertTrue("Duplicate (vocabId, korean) pairs: $dupes", dupes.isEmpty())
    }

    @Test fun coverageReport() {
        val (vocabIds, sentences) = load()
        val covered = sentences.map { it.vocabId }.toSet()
        val uncovered = vocabIds - covered
        // Don't require 100% coverage, just print the gap so it's visible.
        println("Sentence coverage: ${covered.size}/${vocabIds.size} vocab entries")
        if (uncovered.isNotEmpty()) {
            println("Uncovered vocab: $uncovered")
        }
        // Soft threshold: 50% coverage. The corpus is sourced from the actual
        // ROM (corpus.ko.json), so coverage is bounded by which seed words
        // happen to occur in decoded dialog/Pokédex/item text. Many vocab
        // (e.g. 박사, 안녕, 체육관, directions) simply don't appear in the
        // ripped text region, and we deliberately don't fabricate examples.
        val pct = covered.size.toDouble() / vocabIds.size
        assertTrue("Sentence coverage too low: $pct (want >= 0.50)", pct >= 0.50)
    }

    private fun load(): Pair<Set<String>, List<com.poketrek.moneo.data.SentenceEntry>> {
        val vocab = SeedLoader.parse(File(assetsDir, "seed-vocab-ko.json").readText())
        val sentences = SentenceLoader.parse(File(assetsDir, "sentences-ko.json").readText())
        return vocab.map { it.id }.toSet() to sentences
    }
}
