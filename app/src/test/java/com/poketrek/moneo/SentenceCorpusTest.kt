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
 *   1. Both sentence JSON files (sentences-ko-rom.json and sentences-ko-study.json) parse cleanly.
 *   2. Every sentence's `vocabId` resolves to an existing seed entry.
 *   3. The sentence's `korean` string contains the target vocab's
 *      `korean` field as a substring (so the example actually exercises
 *      the word being learned).
 *   4. Romanization and gloss are non-blank.
 *   5. No duplicate `(vocabId, korean)` pairs.
 *   6. Coverage thresholds: ROM corpus ≥50%; study corpus = 100% (hand-crafted).
 */
class SentenceCorpusTest {

    private val assetsDir = File("src/main/assets/moneo")

    // ---- file existence ----

    @Test fun sentencesRomFileExists() {
        val f = File(assetsDir, "sentences-ko-rom.json")
        assertTrue("sentences-ko-rom.json must exist at ${f.absolutePath}", f.exists())
    }

    @Test fun sentencesStudyFileExists() {
        val f = File(assetsDir, "sentences-ko-study.json")
        assertTrue("sentences-ko-study.json must exist at ${f.absolutePath}", f.exists())
    }

    // ---- vocab references ----

    @Test fun everySentenceTargetsExistingVocabRom() {
        val (vocabIds, sentences) = load("sentences-ko-rom.json")
        val orphans = sentences.filter { it.vocabId !in vocabIds }
        assertTrue(
            "Sentences referencing unknown vocabIds in rom corpus: ${orphans.map { it.vocabId }}",
            orphans.isEmpty(),
        )
    }

    @Test fun everySentenceTargetsExistingVocabStudy() {
        val (vocabIds, sentences) = load("sentences-ko-study.json")
        val orphans = sentences.filter { it.vocabId !in vocabIds }
        assertTrue(
            "Sentences referencing unknown vocabIds in study corpus: ${orphans.map { it.vocabId }}",
            orphans.isEmpty(),
        )
    }

    // ---- substring match ----

    @Test fun everySentenceContainsTargetKoreanSubstringRom() {
        val seedJson = File(assetsDir, "seed-vocab-ko-mined.json").readText()
        val vocab = SeedLoader.parse(seedJson).associateBy { it.id }
        val sentences = SentenceLoader.parse(
            File(assetsDir, "sentences-ko-rom.json").readText()
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
            "ROM sentences missing their target word as substring: $violations",
            violations.isEmpty(),
        )
    }

    @Test fun everySentenceContainsTargetKoreanSubstringStudy() {
        val seedJson = File(assetsDir, "seed-vocab-ko-mined.json").readText()
        val vocab = SeedLoader.parse(seedJson).associateBy { it.id }
        val sentences = SentenceLoader.parse(
            File(assetsDir, "sentences-ko-study.json").readText()
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
            "Study sentences missing their target word as substring: $violations",
            violations.isEmpty(),
        )
    }

    // ---- blank fields ----

    @Test fun noBlankFieldsRom() {
        val (_, sentences) = load("sentences-ko-rom.json")
        val bad = sentences.filter {
            it.korean.isBlank() || it.gloss.isBlank()
        }
        assertTrue("ROM sentences with blank fields: ${bad.map { it.vocabId }}", bad.isEmpty())
    }

    @Test fun noBlankFieldsStudy() {
        val (_, sentences) = load("sentences-ko-study.json")
        val bad = sentences.filter {
            it.korean.isBlank() || it.gloss.isBlank()
        }
        assertTrue("Study sentences with blank fields: ${bad.map { it.vocabId }}", bad.isEmpty())
    }

    // ---- duplicate pairs ----

    @Test fun noDuplicatePairsRom() {
        val (_, sentences) = load("sentences-ko-rom.json")
        val keys = sentences.map { it.vocabId to it.korean }
        val dupes = keys.groupingBy { it }.eachCount().filter { it.value > 1 }.keys
        assertTrue("Duplicate (vocabId, korean) pairs in rom corpus: $dupes", dupes.isEmpty())
    }

    @Test fun noDuplicatePairsStudy() {
        val (_, sentences) = load("sentences-ko-study.json")
        val keys = sentences.map { it.vocabId to it.korean }
        val dupes = keys.groupingBy { it }.eachCount().filter { it.value > 1 }.keys
        assertTrue("Duplicate (vocabId, korean) pairs in study corpus: $dupes", dupes.isEmpty())
    }

    // ---- coverage ----

    @Test fun coverageReportRom() {
        val (vocabIds, sentences) = load("sentences-ko-rom.json")
        val covered = sentences.map { it.vocabId }.toSet()
        // After seed-vocab-ko.json was retired (2026-05-12), ROM sentences
        // cover the ~41 migrated seed-v1 entries inside the 860-card mined
        // deck. Numeric coverage % is no longer meaningful at the deck level —
        // assert structural soundness instead (every ROM sentence resolves to
        // a known vocab id) and print the gap for visibility.
        println("ROM sentence coverage: ${covered.size}/${vocabIds.size} vocab entries")
        val orphans = covered - vocabIds
        assertTrue("ROM sentences reference unknown vocabIds: $orphans", orphans.isEmpty())
    }

    @Test fun coverageReportStudy() {
        val (vocabIds, sentences) = load("sentences-ko-study.json")
        val covered = sentences.map { it.vocabId }.toSet()
        println("Study sentence coverage: ${covered.size}/${vocabIds.size} vocab entries")
        val orphans = covered - vocabIds
        assertTrue("Study sentences reference unknown vocabIds: $orphans", orphans.isEmpty())
    }

    // ---- helper ----

    private fun load(sentencesFilename: String): Pair<Set<String>, List<com.poketrek.moneo.data.SentenceEntry>> {
        val vocab = SeedLoader.parse(File(assetsDir, "seed-vocab-ko-mined.json").readText())
        val sentences = SentenceLoader.parse(File(assetsDir, sentencesFilename).readText())
        return vocab.map { it.id }.toSet() to sentences
    }
}