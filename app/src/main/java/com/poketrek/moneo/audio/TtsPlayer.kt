package com.poketrek.moneo.audio

import android.content.Context
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Log
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.Locale

/**
 * Korean Text-to-Speech wrapper for example-sentence playback.
 *
 * Many Samsung devices ship with Google TTS as the default engine but
 * Samsung TTS as the only one with Korean voice data installed (or vice
 * versa). Asking the default engine and giving up if it doesn't speak
 * Korean made the warning card appear on perfectly capable phones, so we
 * now probe each installed engine in turn and use the first one that
 * succeeds with `setLanguage(KOREAN)`. Only when *every* engine has
 * declined do we surface the help card.
 */
class TtsPlayer(context: Context) {
    enum class Status {
        /** Engine init hasn't completed yet — UI should wait, not warn. */
        INITIALIZING,
        /** Korean voice loaded, ready to speak. */
        READY,
        /** Engine works but Korean voice data isn't installed. */
        MISSING_DATA,
        /** No installed TTS engine reports Korean support. */
        UNSUPPORTED,
        /** Engine itself failed to start. */
        ENGINE_FAILED,
    }

    private val _status = MutableStateFlow(Status.INITIALIZING)
    val status: StateFlow<Status> = _status.asStateFlow()

    private val _available = MutableStateFlow(false)
    val available: StateFlow<Boolean> = _available.asStateFlow()

    /**
     * True while a Korean utterance is actively being spoken. Driven by
     * [UtteranceProgressListener]; observers (e.g. [EmulatorScreen]) use
     * this to duck the game's [AudioTrack] so the spoken Korean isn't
     * drowned out by the GBA soundtrack.
     */
    private val _isSpeaking = MutableStateFlow(false)
    val isSpeaking: StateFlow<Boolean> = _isSpeaking.asStateFlow()

    @Volatile private var pendingRate: Float = 1f

    private val appContext = context.applicationContext

    /** Engines we've already attempted, by package name. */
    private val triedEngines = mutableSetOf<String>()

    /** Worst observed failure across attempts; chosen so MISSING_DATA wins
     *  over UNSUPPORTED — "you have an engine, just install the voice" is
     *  a more actionable hint than "no engine speaks Korean." */
    private var fallbackStatus: Status? = null

    /** The currently-mounted TTS instance. Replaced as we probe engines. */
    @Volatile private var tts: TextToSpeech? = null

    /** Engine name we asked for in the latest `startEngine` call. Used by
     *  [handleInit] because TextToSpeech.defaultEngine returns the *system*
     *  default, not the engine this instance is using. */
    @Volatile private var pendingEngineName: String? = null

    private val progressListener = object : UtteranceProgressListener() {
        override fun onStart(utteranceId: String?) { _isSpeaking.value = true }
        override fun onDone(utteranceId: String?) { _isSpeaking.value = false }
        override fun onStop(utteranceId: String?, interrupted: Boolean) {
            _isSpeaking.value = false
        }
        @Deprecated("Pre-API 21 fallback; the variant with errorCode is preferred.")
        override fun onError(utteranceId: String?) { _isSpeaking.value = false }
        override fun onError(utteranceId: String?, errorCode: Int) {
            _isSpeaking.value = false
        }
    }

    init {
        // Try the system-default engine first; it's usually what the user
        // expects and avoids unnecessary engine churn on devices where it
        // already supports Korean.
        startEngine(engineName = null)
    }

    private fun startEngine(engineName: String?) {
        pendingEngineName = engineName
        val previous = tts
        tts = null
        previous?.let {
            runCatching { it.stop(); it.shutdown() }
        }
        val instance = if (engineName != null) {
            TextToSpeech(appContext, { handleInit(it) }, engineName)
        } else {
            TextToSpeech(appContext, { handleInit(it) })
        }
        tts = instance
    }

    private fun handleInit(status: Int) {
        val current = tts ?: return
        val engineName = pendingEngineName ?: current.defaultEngine ?: ""
        if (engineName.isNotEmpty()) triedEngines.add(engineName)

        if (status != TextToSpeech.SUCCESS) {
            Log.w(TAG, "TTS engine '$engineName' init failed (status=$status)")
            if (fallbackStatus == null) fallbackStatus = Status.ENGINE_FAILED
            tryNextEngine(current)
            return
        }
        val r = current.setLanguage(Locale.KOREAN)
        val ok = r == TextToSpeech.LANG_AVAILABLE ||
            r == TextToSpeech.LANG_COUNTRY_AVAILABLE ||
            r == TextToSpeech.LANG_COUNTRY_VAR_AVAILABLE
        if (ok) {
            current.setSpeechRate(pendingRate)
            current.setOnUtteranceProgressListener(progressListener)
            _available.value = true
            _status.value = Status.READY
            Log.i(TAG, "Korean TTS ready via engine '$engineName'")
            return
        }
        Log.w(TAG, "Engine '$engineName' doesn't speak Korean (setLanguage=$r)")
        // MISSING_DATA beats UNSUPPORTED in the displayed warning, since it's
        // the more actionable case — the user can install the voice pack.
        val mapped = if (r == TextToSpeech.LANG_MISSING_DATA) Status.MISSING_DATA
            else Status.UNSUPPORTED
        if (fallbackStatus != Status.MISSING_DATA) fallbackStatus = mapped
        tryNextEngine(current)
    }

    private fun tryNextEngine(current: TextToSpeech) {
        val engines = runCatching { current.engines }.getOrNull() ?: emptyList()
        val candidate = engines.firstOrNull { it.name != null && it.name !in triedEngines }
        if (candidate != null) {
            Log.i(TAG, "Trying alternate TTS engine: '${candidate.name}'")
            startEngine(candidate.name)
        } else {
            _available.value = false
            _status.value = fallbackStatus
                ?: if (engines.isEmpty()) Status.ENGINE_FAILED else Status.UNSUPPORTED
        }
    }

    /**
     * Speak [text] in Korean. Replaces any in-flight utterance (rapid
     * taps don't queue up). No-op until [available] becomes true.
     */
    fun speak(text: String) {
        if (!_available.value) return
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, UTTERANCE_ID)
    }

    /**
     * Set the synthesis rate. 1.0 is normal; 0.5 is half-speed, 2.0
     * double-speed. Safe to call before init completes — the value is
     * cached and applied once the engine is ready.
     */
    fun setRate(rate: Float) {
        val clamped = rate.coerceIn(0.5f, 2.0f)
        pendingRate = clamped
        if (_available.value) tts?.setSpeechRate(clamped)
    }

    /** Cancel anything currently playing. */
    fun stop() {
        tts?.stop()
        _isSpeaking.value = false
    }

    /**
     * Release the platform engine. Called when the owning module is being
     * torn down — Android also reclaims TTS resources on process death so
     * this is mainly defensive for tests / explicit cleanup.
     */
    fun shutdown() {
        runCatching { tts?.stop(); tts?.shutdown() }
        tts = null
        _available.value = false
    }

    companion object {
        private const val TAG = "TtsPlayer"
        private const val UTTERANCE_ID = "moneo-tts"
    }
}
