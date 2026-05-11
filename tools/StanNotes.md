Calibrate flow is wonky. When closing tabing capture badge menu opens and user has to hit capture again to acually capture. 

Badge should stay up after bouncing until player walks manually again

Rom examples in flash cards should have english translation, but all english translations should be toggling in review ui just like pronuciation is currently

No spoilers is set but still seeing rom example sometimes

## TODO: wire up browser-automation MCP

Need a browser-MCP server so Claude can read auth-gated Korean sites
(cafe.naver.com/hansicgu, namu.wiki) for FRLG 2024 patch internals.

Pick one:
- `@playwright/mcp` (Microsoft) — connect to a running Chrome via
  `--connect-url ws://localhost:9222`, preserves Naver login. Best fit.
- `chrome-devtools-mcp` (Google) — same shape, also attaches to running
  Chrome.
- `@modelcontextprotocol/server-puppeteer` — spawns its own browser,
  loses your login. Avoid.

Setup sketch:
1. Start Chrome with `--remote-debugging-port=9222 --user-data-dir=...`
   (clone profile or run a separate Chrome instance pointing at your
   normal cookies — DO NOT share the live profile, Chrome locks the
   profile dir).
2. Add to `~/.claude.json` or project `.mcp.json`:
   ```
   "playwright": { "command": "npx",
       "args": ["@playwright/mcp@latest", "--connect-url",
                "http://localhost:9222"] }
   ```
3. Restart Claude Code, verify with `claude mcp list`.

Purpose: pull the 2024 patch's encoding table / build scripts / font
binary if the authors posted any of it in 한식구 cafe — would replace
the slow context-triangulation rounds.

## TODO: LIS anchor reconciliation

Round-9 agents (chunk 1 & chunk 3 reports) independently flagged the
same cluster of codepoints whose LIS bracket disagrees with corpus
context — likely a nearby anchor is wrong. These are the high-frequency
unknowns that survive all context rounds:

- **0x3A37 (339 occ)**, **0x3B38 (339 occ)**, **0x3E3D (213 occ)** —
  same trio that survived round 7. Bracket says one thing, context
  demands another.
- **0x3D3C / 0x3D38 / 0x3D39** — bracket size 1 (웄/욹-욿) but
  contexts demand common verb stems (일/어/없).
- **0x3920 / 0x3921 / 0x3923** — bracket [된, 두] but contexts often
  want 됐 (U+B410), which is *before* 0x391F=된 in unicode → either
  0x391F=된 is misanchored or there's a font reordering.
- **0x3A3D** — bracket = {맏} alone but context wants 맞 (U+B9DE).
- **0x3C98 / 0x3828 (씩/까)** — appear adjacent in the same word;
  "하나씩" works but "가까이" requires both glyphs outside their
  brackets → joint anchor reset needed.
- **0x3CFA / 0x3CFE** — bracket = {옇} alone (squeezed by round 9's
  0x3CEE=옆 + 0x3D01=예). Context wants "순" (0x3CFE=순격투/순데이트),
  "신/현" (0x3CFA=신챔피언/현챔피언). Could mean either 0x3CEE=옆 is
  itself wrong, OR ROM cp ordering near 옆 deviates from Unicode.

Approach when picking this up: rather than another round of label_X.py,
write a *reconcile* tool that lets the user point at a suspect anchor,
tries pulling it out, and reports which downstream proposals become
internally consistent. The structural problem is that one bad anchor
poisons the LIS bracket for every cp in its neighborhood.