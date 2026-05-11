#!/usr/bin/env bash
# Launch a dedicated Chrome instance with remote-debugging-port for the
# Playwright MCP server to attach to. This runs ON TOP of your existing
# Chrome — it uses a separate profile dir so your main browser stays
# untouched.
#
# Usage:
#   tools/browser-mcp-chrome.sh
#
# First time only: in the Chrome window that opens, log in to
# cafe.naver.com (and any other auth-gated site you want Claude to read).
# Your login cookies persist in $PROFILE_DIR so you only do this once.
#
# Then: restart Claude Code. Playwright MCP will attach automatically
# via the CDP endpoint configured in .mcp.json.
set -euo pipefail

PROFILE_DIR="${HOME}/.poketrek-browser-profile"
DEBUG_PORT="${POKETREK_CHROME_DEBUG_PORT:-9222}"

CHROME=""
for candidate in \
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    "/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta" \
    "/Applications/Chromium.app/Contents/MacOS/Chromium" \
    "$(command -v google-chrome 2>/dev/null || true)" \
    "$(command -v chromium 2>/dev/null || true)"; do
  if [[ -n "$candidate" && -x "$candidate" ]]; then
    CHROME="$candidate"
    break
  fi
done

if [[ -z "$CHROME" ]]; then
  echo "Chrome/Chromium not found. Install Google Chrome." >&2
  exit 1
fi

mkdir -p "$PROFILE_DIR"

echo "Launching Chrome (debug port $DEBUG_PORT, profile $PROFILE_DIR)"
echo "When Chrome opens, log in to any sites you want Claude to read."
echo "Leave this terminal running. To stop: close the Chrome window."

exec "$CHROME" \
  --remote-debugging-port="$DEBUG_PORT" \
  --user-data-dir="$PROFILE_DIR" \
  --no-first-run \
  --no-default-browser-check \
  about:blank
