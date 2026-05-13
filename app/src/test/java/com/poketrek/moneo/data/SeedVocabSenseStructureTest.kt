package com.poketrek.moneo.data

import org.json.JSONObject
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * Build-time invariants on the bundled seed-vocab assets after the
 * 2026-05-13 sense-restructure (see `tools/moneo/restructure_glosses.py`):
 *
 *   1. Every entry has a non-blank `gloss`.
 *   2. `gloss` is a single sense — no top-level `;` separator. Semicolons
 *      inside parentheses are allowed (etymology notes like
 *      `"horse, 馬 (only in 날쌩마; ...)"`).
 *   3. `senses[]` (when present) has no duplicates and never equals `gloss`.
 *   4. Entries tagged with `source: "gMoveNames[N]"` etc. carry the
 *      canonical English from `tools/moneo/name_tables_en.json`. Skips
 *      gracefully if the artifact isn't checked in (so a developer can
 *      run the test suite before running the EN extractor).
 */
class SeedVocabSenseStructureTest {

    private val assetsDir = File("src/main/assets/moneo")
    private val seedFiles = listOf(
        "seed-vocab-ko-mined.json",
        "seed-vocab-ko-topik.json",
        "seed-vocab-ko-species.json",
        "seed-vocab-ko-etymology.json",
    )

    @Test fun glossIsNonBlank() {
        forEachEntry { file, e ->
            val gloss = e.optString("gloss")
            assertTrue(
                "$file: '${e.optString("korean")}' has blank gloss",
                gloss.isNotBlank(),
            )
        }
    }

    @Test fun glossIsSingleSense() {
        forEachEntry { file, e ->
            val gloss = e.optString("gloss")
            val violations = topLevelSemicolons(gloss)
            assertTrue(
                "$file: '${e.optString("korean")}' has top-level ';' in gloss: $gloss",
                violations == 0,
            )
        }
    }

    @Test fun sensesIsDedupedAndExcludesPrimary() {
        forEachEntry { file, e ->
            val gloss = e.optString("gloss")
            val senses = e.optJSONArray("senses") ?: return@forEachEntry
            val list = (0 until senses.length()).map { senses.optString(it) }
            assertFalse(
                "$file: '${e.optString("korean")}' senses[] contains primary gloss",
                gloss in list,
            )
            assertTrue(
                "$file: '${e.optString("korean")}' senses[] has duplicates",
                list.size == list.toSet().size,
            )
        }
    }

    @Test fun romTableEntriesMatchCanonicalEnglish() {
        val tablesFile = File("../tools/moneo/name_tables_en.json")
        if (!tablesFile.exists()) {
            println("name_tables_en.json missing — skipping ROM-canonical check")
            return
        }
        val tablesDoc = JSONObject(tablesFile.readText()).getJSONObject("tables")
        val sourceRe = Regex("^(gMoveNames|gAbilityNames|gSpeciesNames|gItems|gPokedexEntries\\.category)\\[(\\d+)]$")

        forEachEntry { file, e ->
            val source = e.optString("source").takeIf { it.isNotBlank() } ?: return@forEachEntry
            val m = sourceRe.matchEntire(source) ?: return@forEachEntry
            val table = tablesDoc.optJSONObject(m.groupValues[1]) ?: return@forEachEntry
            val want = table.optString(m.groupValues[2]).takeIf { it.isNotBlank() }
                ?: return@forEachEntry
            val got = e.optString("gloss")
            assertTrue(
                "$file: '${e.optString("korean")}' ($source) gloss '$got' != EN ROM canon '$want'",
                got == want,
            )
        }
    }

    // ---- helpers ----

    private fun forEachEntry(check: (file: String, entry: JSONObject) -> Unit) {
        for (name in seedFiles) {
            val f = File(assetsDir, name)
            assertTrue("missing seed asset: ${f.absolutePath}", f.exists())
            val root = JSONObject(f.readText())
            val arr = root.getJSONArray("entries")
            for (i in 0 until arr.length()) {
                check(name, arr.getJSONObject(i))
            }
        }
    }

    private fun topLevelSemicolons(s: String): Int {
        var depth = 0
        var hits = 0
        for (ch in s) {
            when (ch) {
                '(', '[', '{' -> depth++
                ')', ']', '}' -> if (depth > 0) depth--
                ';' -> if (depth == 0) hits++
            }
        }
        return hits
    }
}
