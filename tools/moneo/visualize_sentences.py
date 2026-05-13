#!/usr/bin/env python3
"""Generate `tools/moneo/sentence_browser.html`, a browsable view of every
non-spoiler (LLM-generated) example sentence in the moneo corpus.

Reading this list is the cheapest way to spot bad LLM output and decide
which sentences to flag via the in-app Report flow. The page surfaces:
  - Cheap heuristic warnings (target form missing from KR, thin EN gloss,
    placeholder-looking gloss, double whitespace).
  - Filter chips per corpus and free-text search across KR / EN / vocab.

The page is self-contained — open it directly or serve it via the running
Python HTTP server in `tools/moneo/`.
"""
from __future__ import annotations
import json
import sys
from html import escape
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
ROOT = THIS_DIR.parents[1]
ASSETS = ROOT / "app/src/main/assets/moneo"
OUT_HTML = THIS_DIR / "sentence_browser.html"

LLM_CORPORA = [
    "sentences-ko-etymology.json",
    "sentences-ko-study.json",
    "sentences-ko-themed.json",
    "sentences-ko-themed-mined.json",
    "sentences-ko-themed-species.json",
    "sentences-ko-themed-topik.json",
]


def heuristic_flags(e: dict, corpus: str) -> list[str]:
    """Cheap rule-based warnings that surface likely-bad LLM output without
    requiring a re-audit. The flags are deliberately conservative so the
    page doesn't drown in false positives — the etymology corpus, in
    particular, is intentionally terse (Pokémon names) and uses
    morphological (not substring) connections between the headword and
    the example, so off-target/thin-KR are suppressed there.
    """
    flags: list[str] = []
    ko = (e.get("korean") or "").strip()
    en = (e.get("gloss") or "").strip()
    tf = (e.get("targetForm") or "").strip()
    is_etymology = "etymology" in corpus
    if not is_etymology:
        if tf and tf not in ko:
            flags.append("off-target")
        if not ko or len(ko) < 4:
            flags.append("thin-KR")
    if not en or len(en) < 4:
        flags.append("thin-EN")
    if ko.count("·") >= 2 or ("(" in en and ")" in en and len(en) < 20):
        flags.append("placeholder-EN")
    if "  " in ko or "  " in en:
        flags.append("double-space")
    return flags


def collect_rows() -> tuple[list[dict], dict[str, int]]:
    rows: list[dict] = []
    by_corpus: dict[str, int] = {}
    for fn in LLM_CORPORA:
        p = ASSETS / fn
        if not p.exists():
            continue
        doc = json.loads(p.read_text(encoding="utf-8"))
        for e in doc.get("entries", []):
            if not (e.get("generator") or "").startswith("llm-"):
                continue
            flags = heuristic_flags(e, fn)
            rows.append({
                "corpus": fn,
                "vocabId": e.get("vocabId", ""),
                "korean": e.get("korean", ""),
                "gloss": e.get("gloss", ""),
                "targetForm": e.get("targetForm", ""),
                "areaId": e.get("areaId", ""),
                "generator": e.get("generator", ""),
                "flags": flags,
            })
            by_corpus[fn] = by_corpus.get(fn, 0) + 1
    return rows, by_corpus


def render(rows: list[dict], by_corpus: dict[str, int]) -> str:
    total = len(rows)
    flagged = sum(1 for r in rows if r["flags"])
    clean = total - flagged

    rows_sorted = sorted(rows, key=lambda r: (
        0 if r["flags"] else 1,
        r["corpus"],
        r["vocabId"],
    ))

    parts: list[str] = []
    parts.append("<!DOCTYPE html><html><head><meta charset='utf-8'>")
    parts.append("<title>Moneo non-spoiler examples — browser</title>")
    parts.append("""<style>
:root { color-scheme: dark; }
body { font: 13px/1.45 -apple-system, BlinkMacSystemFont, Helvetica, sans-serif;
       background:#0f1217; color:#dde2ec; margin:0; padding:20px; }
h1 { font-size:18px; margin:0 0 4px; }
.meta { color:#7a8294; font-size:12px; margin-bottom:14px; }
.summary { display:grid; grid-template-columns:repeat(4, 1fr); gap:8px; margin:14px 0; }
.box { background:#1a1f29; border:1px solid #2a2f3a; border-radius:6px; padding:10px; }
.box .n { font-size:22px; font-weight:600; }
.box .lbl { color:#7a8294; font-size:11px; text-transform:uppercase; letter-spacing:0.04em; }
.chips { display:flex; flex-wrap:wrap; gap:6px; margin:8px 0; }
.chip { background:#1a1f29; border:1px solid #2a2f3a; color:#cdd6e3; padding:3px 10px;
        border-radius:14px; font-size:11px; cursor:pointer; user-select:none; }
.chip:hover { background:#23293a; }
.chip.active { background:#3b5891; border-color:#5274c3; color:#fff; }
.controls { display:flex; align-items:center; gap:12px; margin:10px 0 14px; flex-wrap:wrap; }
.controls input { background:#1a1f29; border:1px solid #2a2f3a; color:#cdd6e3;
                  padding:6px 10px; border-radius:6px; font-size:13px; min-width:240px; }
.row { background:#11141b; border:1px solid #1a1f29; border-radius:6px; padding:10px 12px;
       margin:6px 0; display:grid; grid-template-columns:1fr 240px; gap:10px; }
.row.audited { border-color:#5a2828; }
.row.flagged { border-color:#5a4a28; }
.ko  { font-family:ui-monospace,Menlo,monospace; font-size:14px; color:#e6ebf5; }
.en  { color:#9ec3ff; font-size:12px; margin-top:2px; }
.meta2 { color:#7a8294; font-size:11px; margin-top:4px; }
.verdict, .flag { font-size:10px; padding:2px 6px; border-radius:3px; display:inline-block; margin-right:4px; }
.verdict { background:#3a1a1a; color:#ff8a8a; }
.flag    { background:#382a14; color:#f0c46c; }
.issue { color:#cdd6e3; font-size:11px; background:#1a1417; border-left:3px solid #5a2828;
         padding:6px 8px; margin-top:6px; border-radius:0 4px 4px 0; }
.side  { text-align:right; color:#7a8294; font-size:11px; font-family:ui-monospace,Menlo,monospace; }
.hide  { display:none !important; }
</style></head><body>""")

    parts.append("<h1>Non-spoiler example sentences</h1>")
    parts.append(f"<div class='meta'>{total:,} LLM-generated example sentences. "
                 f"Reports filed via the in-app dialog can correct either side.</div>")

    parts.append("<div class='summary' style='grid-template-columns:repeat(3, 1fr)'>")
    parts.append(f"<div class='box'><div class='lbl'>Total non-spoiler</div><div class='n'>{total:,}</div></div>")
    parts.append(f"<div class='box'><div class='lbl'>Heuristic-flagged</div><div class='n' style='color:#f0c46c'>{flagged}</div></div>")
    parts.append(f"<div class='box'><div class='lbl'>Unflagged</div><div class='n' style='color:#7ee69a'>{clean}</div></div>")
    parts.append("</div>")

    parts.append("<div class='controls'>"
                 "<input id='q' placeholder='Search Korean / English / headword …'>"
                 "<span class='chip active' data-filter='all'>All</span>"
                 "<span class='chip' data-filter='flagged'>Flagged</span>"
                 "<span class='chip' data-filter='clean'>Unflagged</span>"
                 "</div>")
    parts.append("<div class='chips'>")
    for c, n in sorted(by_corpus.items()):
        short = c.replace("sentences-ko-", "").replace(".json", "")
        parts.append(f"<span class='chip' data-corpus='{escape(c)}'>{escape(short)} · {n}</span>")
    parts.append("</div>")

    parts.append("<div id='rows'>")
    for r in rows_sorted:
        cls = ["row"]
        if r["flags"]: cls.append("flagged")
        flag_str = " ".join(r["flags"])
        search_blob = " ".join((
            r["korean"], r["gloss"], r["vocabId"], r["targetForm"]
        )).lower()
        parts.append(f"<div class='{' '.join(cls)}' "
                     f"data-corpus='{escape(r['corpus'])}' "
                     f"data-flags='{escape(flag_str)}' "
                     f"data-search='{escape(search_blob)}'>")
        parts.append("<div>")
        parts.append(f"<div class='ko'>{escape(r['korean'])}</div>")
        parts.append(f"<div class='en'>{escape(r['gloss'])}</div>")
        parts.append(f"<div class='meta2'>{escape(r['vocabId'])}"
                     + (f" · target <b>{escape(r['targetForm'])}</b>" if r['targetForm'] else "")
                     + (f" · area {escape(r['areaId'])}" if r['areaId'] else "")
                     + "</div>")
        parts.append("</div>")
        short = r["corpus"].replace("sentences-ko-", "").replace(".json", "")
        parts.append(f"<div class='side'>{escape(short)}</div>")
        parts.append("</div>")
    parts.append("</div>")

    parts.append("""<script>
const q = document.getElementById('q');
const rows = Array.from(document.querySelectorAll('#rows .row'));
let bucketFilter = 'all';
let corpusFilter = null;

function applyFilters() {
  const needle = q.value.trim().toLowerCase();
  for (const r of rows) {
    let visible = true;
    if (bucketFilter === 'flagged' && !r.classList.contains('flagged')) visible = false;
    if (bucketFilter === 'clean'   && r.classList.contains('flagged')) visible = false;
    if (corpusFilter && r.dataset.corpus !== corpusFilter) visible = false;
    if (needle && !r.dataset.search.includes(needle)) visible = false;
    r.classList.toggle('hide', !visible);
  }
}

q.addEventListener('input', applyFilters);
document.querySelectorAll('.chip[data-filter]').forEach(c => {
  c.addEventListener('click', () => {
    document.querySelectorAll('.chip[data-filter]').forEach(x => x.classList.remove('active'));
    c.classList.add('active');
    bucketFilter = c.dataset.filter;
    applyFilters();
  });
});
document.querySelectorAll('.chip[data-corpus]').forEach(c => {
  c.addEventListener('click', () => {
    if (corpusFilter === c.dataset.corpus) {
      corpusFilter = null;
      c.classList.remove('active');
    } else {
      document.querySelectorAll('.chip[data-corpus]').forEach(x => x.classList.remove('active'));
      corpusFilter = c.dataset.corpus;
      c.classList.add('active');
    }
    applyFilters();
  });
});
</script></body></html>""")
    return "".join(parts)


def main() -> int:
    rows, by_corpus = collect_rows()
    html = render(rows, by_corpus)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT_HTML} ({len(html):,} bytes)")
    print(f"  total non-spoiler: {len(rows)}")
    print(f"  heuristic flagged: {sum(1 for r in rows if r['flags'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
