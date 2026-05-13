package com.poketrek.moneo.correction

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.net.URLDecoder

class CorrectionReportTest {

    private fun report(
        proposed: String? = "포켓몬은 친구입니다.",
        proposedGloss: String? = null,
        reason: String? = "particle should be 은 not 는",
        generator: String? = "llm-claude-opus-4-7",
    ) = CorrectionReport(
        vocabId = "seed-v1:포켓몬",
        vocabHeadword = "포켓몬",
        vocabGloss = "Pokémon",
        areaId = "pallet_town",
        currentKorean = "포켓몬는 친구입니다.",
        currentGloss = "Pokémon are friends.",
        source = "rom-rec1344",
        speaker = "오키드",
        generator = generator,
        proposedKorean = proposed,
        proposedGloss = proposedGloss,
        reason = reason,
        appVersion = "0.1.0",
        romCrc32 = "0xDAFFECEC",
    )

    @Test fun jsonRoundTripsEveryField() {
        val r = report()
        val parsed = JSONObject(r.toJson())
        assertEquals(r.vocabId, parsed.getString("vocab_id"))
        assertEquals(r.vocabHeadword, parsed.getString("vocab_headword"))
        assertEquals(r.vocabGloss, parsed.getString("vocab_gloss"))
        assertEquals(r.areaId, parsed.getString("area_id"))
        assertEquals(r.currentKorean, parsed.getString("current_korean"))
        assertEquals(r.currentGloss, parsed.getString("current_gloss"))
        assertEquals(r.source, parsed.getString("source"))
        assertEquals(r.speaker, parsed.getString("speaker"))
        assertEquals(r.generator, parsed.getString("generator"))
        assertEquals(r.proposedKorean, parsed.getString("proposed_korean"))
        // proposed_gloss serializes to null when unset; round-trip the
        // populated path through copy() so the assertion runs against a
        // non-null value too.
        val withGloss = r.copy(proposedGloss = "Pokémon ARE friends.")
        assertEquals(
            "Pokémon ARE friends.",
            JSONObject(withGloss.toJson()).getString("proposed_gloss"),
        )
        assertEquals(r.reason, parsed.getString("reason"))
        assertEquals(r.appVersion, parsed.getString("app_version"))
        assertEquals(r.romCrc32, parsed.getString("rom_crc32"))
    }

    @Test fun jsonEncodesNullableFieldsAsJsonNull() {
        val r = report(proposed = null, reason = null, generator = null)
            .copy(areaId = null, source = null, speaker = null, romCrc32 = null)
        val parsed = JSONObject(r.toJson())
        // JSONObject.NULL serializes to JSON `null`; consumer-side `isNull` works
        listOf(
            "area_id", "source", "speaker", "generator",
            "proposed_korean", "proposed_gloss", "reason", "rom_crc32",
        ).forEach { key ->
            assertTrue("expected JSON null for $key", parsed.isNull(key))
        }
    }

    @Test fun githubUrlContainsAllFieldsUrlEncoded() {
        val r = report()
        val url = buildIssueUrl("Stan-Stani", "poketrek", r)

        assertTrue(url.startsWith("https://github.com/Stan-Stani/poketrek/issues/new?"))
        assertTrue("must reference template", url.contains("template=moneo-correction.yml"))

        // Decode each query value and confirm key fields survived encoding.
        val query = url.substringAfter("?")
        val params = query.split("&").associate { kv ->
            val eq = kv.indexOf('=')
            kv.substring(0, eq) to URLDecoder.decode(kv.substring(eq + 1), "UTF-8")
        }
        assertEquals(r.vocabId, params["vocab-id"])
        assertEquals(r.currentKorean, params["current-korean"])
        assertEquals(r.proposedKorean, params["proposed-korean"])
        // proposed-gloss is empty when the user didn't edit the English side
        // but the form field still appears so GitHub's prefill works.
        assertEquals("", params["proposed-gloss"])
        assertEquals(r.reason, params["reason"])
        assertEquals(r.generator, params["generator"])
        assertEquals(r.romCrc32, params["rom-crc32"])
        assertNotNull(params["title"])
        assertTrue(
            "title should mention the headword",
            params["title"]?.contains(r.vocabHeadword) == true,
        )
    }

    @Test fun githubUrlHandlesEmptyOptionalFields() {
        val r = report(proposed = null, reason = null, generator = null)
        val url = buildIssueUrl("Stan-Stani", "poketrek", r)
        // Empty values should still be present (form fields stay empty rather
        // than disappearing) — this keeps the issue template predictable.
        assertTrue(url.contains("proposed-korean="))
        assertTrue(url.contains("proposed-gloss="))
        assertTrue(url.contains("reason="))
        assertTrue(url.contains("generator="))
    }

    @Test fun proposedGlossSurvivesUrlEncoding() {
        val r = report(proposedGloss = "Pokémon are friends!")
        val url = buildIssueUrl("Stan-Stani", "poketrek", r)
        val params = url.substringAfter("?").split("&").associate { kv ->
            val eq = kv.indexOf('=')
            kv.substring(0, eq) to URLDecoder.decode(kv.substring(eq + 1), "UTF-8")
        }
        assertEquals("Pokémon are friends!", params["proposed-gloss"])
    }

    @Test fun githubUrlStaysWellUnderBrowserLimits() {
        // GitHub URLs handle ~8KB. A typical sentence + reason should be a
        // tiny fraction of that. Catch regressions where someone accidentally
        // dumps the full corpus into the title.
        val r = report(reason = "x".repeat(500))
        val url = buildIssueUrl("Stan-Stani", "poketrek", r)
        assertTrue("URL is ${url.length} chars (>4096)", url.length < 4096)
    }
}
