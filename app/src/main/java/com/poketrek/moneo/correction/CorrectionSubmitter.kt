package com.poketrek.moneo.correction

/**
 * Owner/repo of the GitHub project Korean corrections should be filed
 * against. Edit if the repo is moved or forked. Surfaced into
 * [GithubIssueSubmitter]'s URL builder.
 */
const val DEFAULT_GITHUB_REPO_OWNER = "Stan-Stani"
const val DEFAULT_GITHUB_REPO_NAME = "poketrek"

/**
 * One way to ship a [CorrectionReport] off to a maintainer. Implementations
 * own their own side-effect (open browser, POST to server, etc.); the
 * dialog just renders one button per available submitter.
 */
sealed interface CorrectionSubmitter {
    /** Short label for the dialog button (e.g. "GitHub Issue", "Send to server"). */
    val displayName: String

    /**
     * Ship [report]. Returns success/failure so the dialog can show a
     * Snackbar without baking the UI into each submitter.
     *
     * Suspending so VPS implementations can do real I/O without blocking
     * the UI thread; the GitHub one returns immediately after firing the
     * intent.
     */
    suspend fun submit(report: CorrectionReport): Result<Unit>
}
