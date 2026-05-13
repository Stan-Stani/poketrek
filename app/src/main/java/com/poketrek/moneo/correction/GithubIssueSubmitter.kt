package com.poketrek.moneo.correction

import android.content.Context
import android.content.Intent
import android.net.Uri
import java.net.URLEncoder

/**
 * Opens a pre-filled GitHub Issue Form in the device browser.
 *
 * The form's field IDs (`vocab-id`, `current-korean`, `current-gloss`,
 * `proposed-korean`, `proposed-gloss`, `reason`, `app-version`,
 * `rom-crc32`, `source`, `generator`) MUST match the `id:` values in
 * `.github/ISSUE_TEMPLATE/moneo-correction.yml`.
 * GitHub Issue Forms read URL query params and pre-populate fields by
 * matching `id`.
 *
 * Field caveats:
 *  - Single-line text inputs ignore newlines if the value contains them.
 *  - Multi-line textareas accept everything up to GitHub's URL length cap.
 *  - The pre-filled URL itself can be ~8 KB before browsers start truncating
 *    in practice — well above what any single sentence + reason needs.
 */
class GithubIssueSubmitter(
    private val context: Context,
    private val owner: String,
    private val repo: String,
) : CorrectionSubmitter {

    override val displayName: String = "GitHub Issue"

    override suspend fun submit(report: CorrectionReport): Result<Unit> = runCatching {
        val url = buildIssueUrl(owner, repo, report)
        val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(intent)
    }
}

internal fun buildIssueUrl(owner: String, repo: String, report: CorrectionReport): String {
    val params = listOf(
        "template" to "moneo-correction.yml",
        "title" to "[moneo] Correction: ${report.vocabHeadword}",
        "vocab-id" to report.vocabId,
        "vocab-headword" to "${report.vocabHeadword} / ${report.vocabGloss}",
        "current-korean" to report.currentKorean,
        "current-gloss" to report.currentGloss,
        "proposed-korean" to (report.proposedKorean ?: ""),
        "proposed-gloss" to (report.proposedGloss ?: ""),
        "reason" to (report.reason ?: ""),
        "source" to (report.source ?: ""),
        "speaker" to (report.speaker ?: ""),
        "generator" to (report.generator ?: ""),
        "area-id" to (report.areaId ?: ""),
        "app-version" to report.appVersion,
        "rom-crc32" to (report.romCrc32 ?: ""),
    )
    val query = params.joinToString("&") { (k, v) ->
        "$k=${URLEncoder.encode(v, "UTF-8")}"
    }
    return "https://github.com/$owner/$repo/issues/new?$query"
}
