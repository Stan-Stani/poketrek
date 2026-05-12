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

## Codepoint map session summary (post glyph-id round 2)

Map size: **1161 anchors**. Remaining unknowns: **151 cps / 569 occ**
of which:
- **115 cps / 482 occ** = classified CONTROL bytes in
  `control_codes.json`.
- **36 cps / 87 occ** = genuine unknowns.

Of those 36:
- **6 cps / 42 occ** are the suspected LIS-misanchored alt-encodings
  flagged above (0x3EAD, 0x3CFA, 0x3F3C, 0x40FE, 0x383C, 0x3FFB):
  - 0x3CFA likely 신 or 현 (champion-modifier), 8 occ
  - 0x383C likely 자 (interjection) or 막 (just), 6 occ — fits 4/6
  - 0x3FFB likely 또 or 참 (modifier), 5 occ — fits 5/5 but 또/참
    ambiguous
  - 0x3F3C, 0x40FE, 0x3EAD remain murky even with full sentence
    contexts; will require visual triangulation or patch-source
    confirmation.
- **30 cps / 45 occ** = single-occurrence long-tail. Most need either
  a pixel diff against labeled cps (glyph-dup r2 with larger
  candidate pool) or the 2024 patch's encoding table.

This round (`apply_glyph_id_r2.py`) added:
- 0x400A = 틱 (confirmed via 4× "조이스틱의/과의/을/으로부터의" in
  wireless-adapter strings; bracket says 폴-폼 but the contexts
  are unambiguous, classic alt-encoding pattern)
- 0x3DFF, 0x3BFF, 0x3CFF → CONTROL (sentence terminators, no
  syllable role)
- 0x40FC → CONTROL (inventory-quantity glyph in
  "{item} [40FC] 개" pattern)
- 0x3CFF and 0x40FC upgraded from generic "atlas-hole" placeholder
  to evidence-based hypotheses.

Diminishing returns observation: each remaining unknown now requires
significant analysis for ≤1 occurrence of payoff. The structural
unblocker is the bracket-reconcile tool in the TODO above — without
it, the LIS-misanchored cluster (which contains the highest-value
remaining cps) can't be cracked from context alone.

## Codepoint map session summary (post glyph-dup r2/r3)

Map size: **1184 anchors**. Remaining unknowns: **130 cps / 537 occ**
of which:
- **121 cps / 514 occ** = classified CONTROL bytes in
  `control_codes.json`.
- **9 cps / 23 occ** = genuine unknowns.

Two breakthroughs this session:

1. **Pixel-distance scan with looser threshold (≤8)** unlocked the
   single-occurrence long-tail. Most cps that didn't match at the
   strict ≤4 threshold still pixel-match within ≤8 with high
   confidence (multiple ties at d=2 produced pixel-perfect alt-
   encoding labels: 0x4001=젤, 0x38D8=탬, 0x3E4B=죄).

2. **Blank-glyph CONTROL detection** — `scan_glyph_duplicates`
   already skips blank glyphs, but I hadn't realized this is the
   signature for the StanNotes-flagged LIS-misanchored cluster.
   0x3CFA, 0x40FE, 0x3FFB all have near-empty atlas slots; they
   can't be syllables. These are text-formatting markers (color/
   emphasis/font-switch) appearing mid-word before adjectives/
   nouns. This single observation resolves 3 of the 6 high-value
   "LIS-misanchored common short word" candidates flagged in the
   previous session's TODO.

This session (`apply_glyph_id_r2.py` + `apply_glyph_dup_r2.py` +
`apply_glyph_dup_r3.py`) added 24 alt-encoding labels + 13 control
classifications. Reduction in truly-unknown:

  Start of session:  39 cps / 102 occ
  After glyph-id r2: 36 cps / 87 occ   (-3 cps, -15 occ)
  After glyph-dup r2: 18 cps / 55 occ  (-18 cps, -32 occ)
  After glyph-dup r3:  9 cps / 23 occ  (-9 cps, -32 occ)

Total: **77% reduction in both distinct cps and occurrences**.

## Final 9 truly-unknown codepoints (post-session)

All have weak pixel-match (d≥5) and limited corpus context. Next
steps require either the bracket-reconcile tool or patch-source
confirmation:

- 0x3F3C (7 occ) — likely TM-icon CONTROL (parallel to 0x40A1 HM
  icon); pixel d=8 to any syllable rules out syllable role. Pokédex
  contexts at recs 5140/5141 muddy this.
- 0x3F3A (4 occ) — ambiguous syllable, multiple d=5 ties (램/랭/맹/
  멤/멩); LIS bracket extremely wide (75 candidates → misanchored).
- 0x3FA0 (3 occ) — pixel d=8 best; appears in font-dump records.
- 0x373E (3 occ) — pixel d=8 to all 거-family syllables; bracket
  is 격-견 with only 2 candidates.
- 0x3786 (2 occ), 0x3C93 (1 occ), 0x3820 (1 occ), 0x3884 (1 occ),
  0x3C6C (1 occ) — single-occurrence with weak pixel match.

The structural blocker (bracket-reconcile tool) is still the
right next move for cracking 0x3F3A and 0x373E, but it's no longer
worth blocking on for any single cp — yield-per-effort below
break-even given how rare these are in the corpus.

## Codepoint map: 100% syllable coverage achieved

Stan eyeballed the rendered atlas glyphs for the final 9 unknowns
and labeled them directly:

  0x3F3C = 퀵, 0x3F3A = 퀭, 0x3FA0 = 튄, 0x373E = 겪,
  0x3786 = 궐, 0x3C93 = 씌, 0x3820 = 뀨, 0x3884 = 놨,
  0x3C6C = 쏟

Map size: **1193 anchors**. Truly-unknown codepoints in dialog
region: **0**. All 121 remaining "unknown" entries in
`codepoint_unknowns_2024.json` are confirmed CONTROL bytes
(formatting, icons, terminators, padding).

Final lesson: the very last mile (9 cps, mostly single-occurrence
syllables with weak corpus context) yielded almost instantly to a
human-in-the-loop visual pass with the labeled neighbors rendered
alongside. The reconcile tool wasn't needed in the end — a side-
by-side glyph grid was more effective. Worth remembering for
future calibration projects: invest in glyph visualization before
overengineering inference.