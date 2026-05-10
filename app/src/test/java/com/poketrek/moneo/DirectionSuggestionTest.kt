package com.poketrek.moneo

import com.poketrek.emu.RomVariant
import com.poketrek.moneo.data.FlashcardDirection
import com.poketrek.moneo.ui.suggestDirectionFor
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * The intent matrix that drives the one-time direction-suggestion prompt
 * on first ROM load. Pure-JVM, unaffected by the dialog's Compose layer.
 */
class DirectionSuggestionTest {

    @Test fun usRev1WithKoreanLocaleSuggestsEnToKo() {
        assertEquals(
            FlashcardDirection.EN_TO_KO,
            suggestDirectionFor(RomVariant.LEAFGREEN_US_REV1, "ko"),
        )
    }

    @Test fun usRev1WithEnglishLocaleHasNoSuggestion() {
        // English speaker on the English ROM: forward mode is already the
        // default; no need to nag.
        assertNull(suggestDirectionFor(RomVariant.LEAFGREEN_US_REV1, "en"))
    }

    @Test fun koreanRomsWithEnglishLocaleSuggestKoToEn() {
        assertEquals(
            FlashcardDirection.KO_TO_EN,
            suggestDirectionFor(RomVariant.LEAFGREEN_KOREAN, "en"),
        )
        assertEquals(
            FlashcardDirection.KO_TO_EN,
            suggestDirectionFor(RomVariant.LEAFGREEN_KR_2024, "en"),
        )
    }

    @Test fun koreanRomsWithKoreanLocaleHasNoSuggestion() {
        // Korean speaker on the Korean ROM: KO_TO_EN is already default.
        assertNull(suggestDirectionFor(RomVariant.LEAFGREEN_KR_2024, "ko"))
        assertNull(suggestDirectionFor(RomVariant.LEAFGREEN_KOREAN, "ko"))
    }

    @Test fun unknownRomNeverTriggersSuggestion() {
        assertNull(suggestDirectionFor(RomVariant.UNKNOWN, "ko"))
        assertNull(suggestDirectionFor(RomVariant.UNKNOWN, "en"))
        assertNull(suggestDirectionFor(RomVariant.UNKNOWN, "fr"))
    }

    @Test fun unrelatedLocalesNeverTriggerSuggestion() {
        // Japanese, French, etc. on any variant — we don't know what to
        // suggest, so don't.
        assertNull(suggestDirectionFor(RomVariant.LEAFGREEN_US_REV1, "ja"))
        assertNull(suggestDirectionFor(RomVariant.LEAFGREEN_KR_2024, "fr"))
    }

    @Test fun localeMatchIsCaseInsensitive() {
        assertEquals(
            FlashcardDirection.EN_TO_KO,
            suggestDirectionFor(RomVariant.LEAFGREEN_US_REV1, "KO"),
        )
    }
}
