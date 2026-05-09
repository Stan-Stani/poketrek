package com.poketrek.moneo.correction

import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.net.HttpURLConnection
import java.net.URL

/**
 * POSTs the [CorrectionReport] as JSON to a user-configured endpoint.
 *
 * Stub implementation — single attempt, no retry, no auth, no offline
 * queue. Once the server-side aggregator exists, this is the place to
 * harden (consider OkHttp, exponential backoff, on-disk queue keyed on
 * report content-hash for idempotency).
 *
 * The endpoint is expected to accept `Content-Type: application/json`
 * with the body produced by [CorrectionReport.toJson]. A 2xx response
 * counts as success; anything else surfaces a failure to the caller.
 */
class VpsSubmitter(
    private val endpoint: String,
) : CorrectionSubmitter {

    override val displayName: String = "Send to server"

    override suspend fun submit(report: CorrectionReport): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                val conn = (URL(endpoint).openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    setRequestProperty("Content-Type", "application/json")
                    setRequestProperty("User-Agent", "poketrek-moneo")
                    connectTimeout = 8_000
                    readTimeout = 8_000
                    doOutput = true
                }
                try {
                    conn.outputStream.use { it.write(report.toJson().toByteArray(Charsets.UTF_8)) }
                    val code = conn.responseCode
                    if (code !in 200..299) {
                        error("HTTP $code from $endpoint")
                    }
                    Log.i(TAG, "Correction posted to VPS, status=$code")
                } finally {
                    conn.disconnect()
                }
                Unit
            }
        }

    companion object {
        private const val TAG = "VpsSubmitter"
    }
}
