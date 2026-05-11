Calibrate flow is wonky. When closing tabing capture badge menu opens and user has to hit capture again to acually capture. 

Badge should stay up after bouncing until player walks manually again

Rom examples in flash cards should have english translation, but all english translations should be toggling in review ui just like pronuciation is currently

No spoilers is set but still seeing rom example sometimes

## TODO (USER ACTION): activate browser-automation MCP

Playwright MCP is wired up in `.mcp.json` (project scope) using CDP
attach. To turn it on:

```
# 1. In one terminal, launch the dedicated Chrome instance:
tools/browser-mcp-chrome.sh

# 2. In the Chrome window that opens, log in to cafe.naver.com once.
#    (Cookies persist in ~/.poketrek-browser-profile across runs.)

# 3. Restart Claude Code in the poketrek directory. It will pick up
#    .mcp.json and the playwright tools will be available.
#    Verify with:  claude mcp list
```

After that, Claude can navigate cafe.naver.com/hansicgu (and any other
auth-gated Korean site) directly. The script uses a separate profile
dir, so your main Chrome stays untouched.

Goal: pull the 2024 patch's encoding table / build scripts / font
binary if the authors posted any of it in 한식구 cafe — would
short-circuit the remaining context-triangulation work.

## Codepoint map session summary (as of last regen)

Map size: **1112 anchors**. Remaining unknowns: **194 cps / 835
occurrences** of which:
- **6 cps / 104 occ** = confirmed CONTROL bytes (see
  `tools/moneo/rom_swap/control_codes.json`): 0x3FFF (dialog
  terminator), 0x40A1 (HM/TM icon), 0x3C08/4018/408C/398C (binary
  table bytes outside dialog).
- **188 cps / 731 occ** = genuine unknowns.

Of those 731 unknown occurrences:
- ~250 occ in a handful of cluster cps (0x393A/3938/393C in the
  "마비/잘잠/마비치료" verb-stem cluster, 0x3A40 in "맙소사" cluster,
  0x3D3F adjacent to 0x3D3C=더).
- ~120 occ on 0x4038 alone — almost certainly a sentence-final
  particle/control marker (appears as `오신 것을 [4038]` etc., but
  doesn't fit 환영 cleanly across all 107 contexts). Treat as suspected
  control byte until proven otherwise.
- ~360 occ across 180 long-tail cps with 1-3 occurrences each. Most
  need either an anchor reconciliation tool, an OCR/visual sweep with
  better candidate generation than PIL provides, or the patch sources
  themselves via the browser-MCP path.

What worked best this session (in order of impact-per-effort):

1. **LIS-override context-only labeling** (reconcile r1/r2/r3) —
   recovered 1,550+ occurrences across 21 cps by trusting context over
   broken LIS brackets. Insight: high-freq Korean morphemes (하/있/만/
   곳/그/이/더/요) are pulled into a contiguous mid-range cp block
   regardless of Unicode collation.
2. **Three parallel context agents** (round 9) — 299 labels in a
   single batch.
3. **Polysemous majority-rule pass** — 22 labels, 672 occ, accepting
   ~30% imprecision on alt-encoded syllables.

What didn't yield well (≤25 labels per batch despite real effort):

- PIL-OCR top-N visual picker (visual r1): PIL's candidate ranking is
  too noisy; the right syllable family is often missing from top-8.
- Jamo-structure picker: better, but still capped by ROM-glyph
  ambiguity at 16×16 resolution.

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