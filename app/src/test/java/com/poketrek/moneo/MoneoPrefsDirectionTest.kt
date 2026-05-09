package com.poketrek.moneo

import com.poketrek.moneo.data.FlashcardDirection
import com.poketrek.moneo.data.TtsLanguage
import com.poketrek.moneo.data.effectiveTtsLanguage
import com.poketrek.moneo.data.migrateTtsLegacy
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * Pure-JVM coverage of the direction / TTS-language preference logic that
 * MoneoPrefs delegates to. The MoneoPrefs class itself wraps DataStore +
 * StateFlow plumbing that's out of scope for unit tests; everything here
 * exercises the rules a future maintainer would need to keep correct when
 * touching the persistence layer.
 */
class MoneoPrefsDirectionTest {

    @Test fun directionDefaultsToKoToEnWhenStoredValueMissing() {
        assertEquals(FlashcardDirection.KO_TO_EN, FlashcardDirection.fromStored(null))
        assertEquals(FlashcardDirection.KO_TO_EN, FlashcardDirection.fromStored(""))
        assertEquals(FlashcardDirection.KO_TO_EN, FlashcardDirection.fromStored("garbage"))
    }

    @Test fun directionRoundTripsThroughEnumName() {
        assertEquals(FlashcardDirection.KO_TO_EN, FlashcardDirection.fromStored("KO_TO_EN"))
        assertEquals(FlashcardDirection.EN_TO_KO, FlashcardDirection.fromStored("EN_TO_KO"))
    }

    @Test fun ttsLanguageReturnsNullForMissingOrUnknown() {
        assertNull(TtsLanguage.fromStored(null))
        assertNull(TtsLanguage.fromStored(""))
        assertNull(TtsLanguage.fromStored("FRENCH"))
    }

    @Test fun ttsLanguageRoundTripsThroughEnumName() {
        assertEquals(TtsLanguage.KOREAN, TtsLanguage.fromStored("KOREAN"))
        assertEquals(TtsLanguage.ENGLISH, TtsLanguage.fromStored("ENGLISH"))
        assertEquals(TtsLanguage.OFF, TtsLanguage.fromStored("OFF"))
    }

    @Test fun ttsLanguageDefaultMirrorsDirection() {
        assertEquals(TtsLanguage.KOREAN, TtsLanguage.defaultFor(FlashcardDirection.KO_TO_EN))
        assertEquals(TtsLanguage.ENGLISH, TtsLanguage.defaultFor(FlashcardDirection.EN_TO_KO))
    }

    @Test fun effectiveTtsLanguageHonorsOverride() {
        // Korean user studying English with Korean audio:
        assertEquals(
            TtsLanguage.KOREAN,
            effectiveTtsLanguage(FlashcardDirection.EN_TO_KO, TtsLanguage.KOREAN),
        )
        // English speaker studying Korean but doesn't want any audio:
        assertEquals(
            TtsLanguage.OFF,
            effectiveTtsLanguage(FlashcardDirection.KO_TO_EN, TtsLanguage.OFF),
        )
    }

    @Test fun effectiveTtsLanguageFallsBackToDirectionDefaultWhenNoOverride() {
        assertEquals(
            TtsLanguage.KOREAN,
            effectiveTtsLanguage(FlashcardDirection.KO_TO_EN, override = null),
        )
        assertEquals(
            TtsLanguage.ENGLISH,
            effectiveTtsLanguage(FlashcardDirection.EN_TO_KO, override = null),
        )
    }

    @Test fun migrationKeepsExistingOverride() {
        // If the user has already chosen a language explicitly, never reapply
        // the legacy boolean — they may have set OFF and turned legacy back on
        // (or any other combo).
        assertEquals(
            TtsLanguage.KOREAN,
            migrateTtsLegacy(legacyEnabled = false, existingOverride = TtsLanguage.KOREAN),
        )
        assertEquals(
            TtsLanguage.OFF,
            migrateTtsLegacy(legacyEnabled = true, existingOverride = TtsLanguage.OFF),
        )
    }

    @Test fun migrationConvertsLegacyDisabledToOff() {
        assertEquals(
            TtsLanguage.OFF,
            migrateTtsLegacy(legacyEnabled = false, existingOverride = null),
        )
    }

    @Test fun migrationLeavesOverrideNullForLegacyEnabledOrUnset() {
        // Legacy was true — fall through to direction default; no override.
        assertNull(migrateTtsLegacy(legacyEnabled = true, existingOverride = null))
        // Legacy never persisted (fresh install) — same.
        assertNull(migrateTtsLegacy(legacyEnabled = null, existingOverride = null))
    }
}
