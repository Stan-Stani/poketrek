package com.poketrek.moneo.audio

import android.content.Context
import android.speech.tts.TextToSpeech
import android.util.Log
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.Locale

/**
 * Korean Text-to-Speech wrapper for example-sentence playback. Initializes
 * the platform TTS engine eagerly and surfaces readiness via [available] —
 * the UI hides the speaker button until Korean voice data is loaded
 * (`available` flips true) so taps don't no-op silently. Init is async so
 * the engine may not be ready immediately after construction.
 */
class TtsPlayer(context: Context) {
    private val _available = MutableStateFlow(false)
    val available: StateFlow<Boolean> = _available.asStateFlow()

    @Volatile private var pendingRate: Float = 1f

    private val tts: TextToSpeech = TextToSpeech(context.applicationContext) { status ->
        // The init callback fires on the main thread after the constructor
        // returns, so referencing `tts` here is safe even though it's a val
        // initialized in the same statement.
        if (status == TextToSpeech.SUCCESS) {
            val r = tts.setLanguage(Locale.KOREAN)
            val ok = r == TextToSpeech.LANG_AVAILABLE
                || r == TextToSpeech.LANG_COUNTRY_AVAILABLE
                || r == TextToSpeech.LANG_COUNTRY_VAR_AVAILABLE
            if (!ok) Log.w(TAG, "Korean voice data unavailable (setLanguage=$r)")
            tts.setSpeechRate(pendingRate)
            _available.value = ok
        } else {
            Log.w(TAG, "TTS init failed (status=$status)")
            _available.value = false
        }
    }

    /**
     * Speak [text] in Korean. Replaces any in-flight utterance (rapid
     * taps don't queue up). No-op until [available] becomes true.
     */
    fun speak(text: String) {
        if (!_available.value) return
        tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, UTTERANCE_ID)
    }

    /**
     * Set the synthesis rate. 1.0 is normal; 0.5 is half-speed, 2.0
     * double-speed. Safe to call before init completes — the value is
     * cached and applied once the engine is ready.
     */
    fun setRate(rate: Float) {
        val clamped = rate.coerceIn(0.5f, 2.0f)
        pendingRate = clamped
        if (_available.value) tts.setSpeechRate(clamped)
    }

    /** Cancel anything currently playing. */
    fun stop() {
        tts.stop()
    }

    /**
     * Release the platform engine. Called when the owning module is being
     * torn down — Android also reclaims TTS resources on process death so
     * this is mainly defensive for tests / explicit cleanup.
     */
    fun shutdown() {
        tts.stop()
        tts.shutdown()
        _available.value = false
    }

    companion object {
        private const val TAG = "TtsPlayer"
        private const val UTTERANCE_ID = "moneo-tts"
    }
}
