#!/usr/bin/env python3
"""Generate `tools/moneo/rom_diff.html`, a side-by-side report of what the
canonical EN LeafGreen ROM and the Korean 2024 patch share vs. diverge.

Two views in one self-contained page:
  1. Per-table pairing. The five canonical pokefirered name tables
     (gMoveNames, gAbilityNames, gSpeciesNames, gItems, gPokedexEntries
     category, gTrainerClassNames) live at the same offsets in both ROMs
     because the KR patch was rebuilt over the FRLG layout. Each row is
     classified: `translated` (KR string contains Hangul), `kept-EN`
     (byte-for-byte identical to EN ASCII), `ASCII-different` (KR is ASCII
     but rewritten), `mixed`, or `missing` (KR field empty/garbled).
  2. 64 KB binary chunk heatmap. Walks the two ROMs in 0x10000-byte
     chunks, CRC32-hashes each, and colors the cell green when the chunks
     are byte-identical and red when they differ.

Open the resulting HTML in any browser — no JS framework required.
"""
from __future__ import annotations
import json
import sys
import zlib
from html import escape
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
ROOT = THIS_DIR.parents[1]

sys.path.insert(0, str(THIS_DIR))
from rom_config_en import (
    ROM_PATH_EN, ROM_CRC32_EN,
    GMOVE_NAMES_EN, GMOVE_NAMES_EN_STRIDE, GMOVE_NAMES_EN_N,
    GABILITY_NAMES_EN, GABILITY_NAMES_EN_STRIDE, GABILITY_NAMES_EN_N,
    GSPECIES_NAMES_EN, GSPECIES_NAMES_EN_STRIDE, GSPECIES_NAMES_EN_N,
    GITEMS_EN, GITEMS_EN_STRIDE, GITEMS_EN_N, GITEMS_EN_NAME_OFF,
    GPOKEDEX_ENTRIES_EN, GPOKEDEX_EN_STRIDE, GPOKEDEX_EN_N, GPOKEDEX_EN_CATEGORY_OFF,
    GTRAINER_CLASS_NAMES_EN, GTRAINER_CLASS_NAMES_EN_STRIDE, GTRAINER_CLASS_NAMES_EN_N,
    _build_charmap,
)
from rom_config import ROM_PATH, ROM_CRC32_2024

CODEPOINT_MAP_JSON = THIS_DIR / "rom_swap/codepoint_map.json"
CORPUS_EN_JSON = THIS_DIR / "corpus.en.json"
CORPUS_KR_JSON = THIS_DIR / "corpus.ko.2024.json"
OUT_HTML = THIS_DIR / "rom_diff.html"

# (label, base_off, stride, count, name_off_within_struct, name_field_len)
TABLES = [
    ("gMoveNames",          GMOVE_NAMES_EN,         GMOVE_NAMES_EN_STRIDE,        GMOVE_NAMES_EN_N,        0, GMOVE_NAMES_EN_STRIDE),
    ("gAbilityNames",       GABILITY_NAMES_EN,      GABILITY_NAMES_EN_STRIDE,     GABILITY_NAMES_EN_N,     0, GABILITY_NAMES_EN_STRIDE),
    ("gSpeciesNames",       GSPECIES_NAMES_EN,      GSPECIES_NAMES_EN_STRIDE,     GSPECIES_NAMES_EN_N,     0, GSPECIES_NAMES_EN_STRIDE),
    ("gItems.name",         GITEMS_EN,              GITEMS_EN_STRIDE,             GITEMS_EN_N,             GITEMS_EN_NAME_OFF, 14),
    ("gPokedex.category",   GPOKEDEX_ENTRIES_EN,    GPOKEDEX_EN_STRIDE,           GPOKEDEX_EN_N,           GPOKEDEX_EN_CATEGORY_OFF, 12),
    ("gTrainerClassNames",  GTRAINER_CLASS_NAMES_EN, GTRAINER_CLASS_NAMES_EN_STRIDE, GTRAINER_CLASS_NAMES_EN_N, 0, GTRAINER_CLASS_NAMES_EN_STRIDE),
]

EN_CHARMAP = _build_charmap()


def decode_en(rom: bytes, off: int, field_len: int) -> str:
    out: list[str] = []
    for i in range(field_len):
        b = rom[off + i]
        if b == 0xFF:
            break
        c = EN_CHARMAP.get(b)
        out.append(c if c is not None else f"·")  # unmapped → middot
    return "".join(out).strip()


def decode_kr(rom: bytes, off: int, field_len: int, cp_map: dict[str, str]) -> tuple[str, int]:
    """Decode 16-bit BE codepoints. Returns (text, unknown_count)."""
    out: list[str] = []
    unknown = 0
    i = 0
    while i < field_len:
        b = rom[off + i]
        if b == 0xFF:
            break
        if i + 1 >= field_len:
            break
        cp = (b << 8) | rom[off + i + 1]
        s = cp_map.get(f"{cp:04X}") or cp_map.get(f"{cp:04x}")
        if s is None:
            unknown += 1
            out.append("·")
        else:
            out.append(s)
        i += 2
    return "".join(out).strip(), unknown


def _is_en_placeholder(en: str) -> bool:
    """Pokefirered fills unused species/item slots with `?` or `??????` and
    terminator. Empty (`""`) is the post-terminator zero region. Either is a
    sentinel for "this slot is reserved/unused."
    """
    s = en.strip()
    return s == "" or set(s) <= {"?"}


# Gen III Japanese single-byte charmap. Built from Bulbapedia's "Character
# encoding (Generation III)" Japanese table. Used only to detect "still-JP"
# residue — slots the 명군 2024 KR patch (which is layered on JP LeafGreen
# 1.0) failed to overwrite.
_JP_HIRAGANA = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんぁぃぅぇぉゃゅょがぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽっ"
_JP_KATAKANA = "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲンァィゥェォャュョガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポッ"


def _build_jp_charmap() -> dict[int, str]:
    m: dict[int, str] = {0x00: " "}
    for i, c in enumerate(_JP_HIRAGANA): m[0x01 + i] = c
    for i, c in enumerate(_JP_KATAKANA): m[0x51 + i] = c
    for i, c in enumerate("0123456789"): m[0xA1 + i] = c
    m[0xAB] = "!"; m[0xAC] = "?"; m[0xAD] = "."; m[0xAE] = "-"
    return m


_JP_CHARMAP = _build_jp_charmap()


def jp_decode(raw: bytes) -> str:
    """Decode raw bytes via the Gen III JP single-byte charmap. Stops at the
    0xFF terminator. Used both for `still-JP` detection and as a debug view
    on the HTML row so the reader can judge plausibility.
    """
    out: list[str] = []
    for b in raw:
        if b == 0xFF:
            break
        c = _JP_CHARMAP.get(b)
        out.append(c if c is not None else f"·")
    return "".join(out)


def _looks_japanese(raw: bytes) -> bool:
    """True if the raw bytes plausibly decode as Gen III Japanese text. The
    JP Gen III charmap covers only 0x00-0xAB; any byte above that range is
    either a high control code or, more often here, evidence the bytes are
    NOT plain JP text and belong to some other encoding (compressed glyph,
    extended KR codepoint, etc.). A single out-of-range byte disqualifies.
    """
    n_kana = 0
    n_total = 0
    for b in raw:
        if b == 0xFF:
            break
        n_total += 1
        if b > 0xAE:
            return False  # outside Gen III JP charmap → not plain JP
        c = _JP_CHARMAP.get(b)
        if c and (c in _JP_HIRAGANA or c in _JP_KATAKANA):
            n_kana += 1
    if n_total < 3:
        return False
    return n_kana >= max(2, int(0.6 * n_total))


def classify(en: str, kr: str, kr_unknown: int, raw_kr: bytes) -> str:
    en_placeholder = _is_en_placeholder(en)
    kr_translated = any(0xAC00 <= ord(c) <= 0xD7A3 for c in kr)
    if kr_translated:
        return "translated"
    # Both sides are sentinel/dummy bytes — neither ROM displays this slot.
    # The Gen 3 species table reserves indices 252-276 between Gen 2 and
    # Gen 3 for cut/unused designs; the item table has similar gaps for
    # `ITEM_NONE`, removed items, and debug slots. The KR patch leaves
    # those slots as the EN-encoded `?` + 0xFF, which the KR decoder reads
    # as unknown codepoints.
    if en_placeholder and not kr.strip().strip("·"):
        return "placeholder"
    if not kr.strip():
        return "unmapped"
    # Residue from the JP base ROM that the 명군 KR patch missed.
    if _looks_japanese(raw_kr):
        return "still-JP"
    if kr_unknown > 0 and not any(c.isalpha() for c in kr):
        return "unmapped"
    if all(c.isascii() for c in kr):
        return "ASCII-different"
    return "mixed"


def chunk_diff(en_rom: bytes, kr_rom: bytes, chunk: int = 0x10000):
    out = []
    size = min(len(en_rom), len(kr_rom))
    for off in range(0, size, chunk):
        end = min(off + chunk, size)
        eh = zlib.crc32(en_rom[off:end])
        kh = zlib.crc32(kr_rom[off:end])
        out.append((off, end - off, eh, kh, eh == kh))
    return out


def load_dialog_density(path: Path, rom_size: int, chunk: int = 0x10000) -> tuple[int, int, list[int]]:
    """Returns (record_count, total_chars, per_chunk_record_count[]).

    Pointer-walked text records each have an `offset` and decoded `text`.
    We bucket records by their offset into 64 KB chunks so the heatmap can
    show where dialog actually lives in each ROM.
    """
    n_chunks = (rom_size + chunk - 1) // chunk
    per_chunk = [0] * n_chunks
    total_chars = 0
    records = 0
    if not path.exists():
        return 0, 0, per_chunk
    doc = json.loads(path.read_text(encoding="utf-8"))
    for r in doc.get("records", []):
        off = r.get("offset")
        text = r.get("text", "")
        if off is None:
            continue
        idx = off // chunk
        if 0 <= idx < n_chunks:
            per_chunk[idx] += 1
        records += 1
        total_chars += len(text)
    return records, total_chars, per_chunk


def render_html(en_meta, kr_meta, rows_by_table, summary, chunks, dialog) -> str:
    total_chunk_bytes = sum(sz for _, sz, _, _, _ in chunks)
    identical_chunk_bytes = sum(sz for _, sz, _, _, ok in chunks if ok)
    pct_identical = 100.0 * identical_chunk_bytes / total_chunk_bytes if total_chunk_bytes else 0.0

    grand_translated  = sum(s["translated"] for s in summary.values())
    grand_asciidiff   = sum(s["ASCII-different"] for s in summary.values())
    grand_placeholder = sum(s["placeholder"] for s in summary.values())
    grand_still_jp    = sum(s["still-JP"] for s in summary.values())
    grand_unmapped    = sum(s["unmapped"] for s in summary.values())
    grand_total       = sum(sum(s.values()) for s in summary.values())

    html: list[str] = []
    html.append("<!DOCTYPE html><html><head><meta charset='utf-8'>")
    html.append("<title>LeafGreen EN vs KR 2024 — ROM diff</title>")
    html.append("""<style>
:root { color-scheme: dark; }
body { font: 13px/1.4 -apple-system, BlinkMacSystemFont, Helvetica, sans-serif;
       background:#0f1217; color:#dde2ec; margin:0; padding:24px; }
h1 { font-size:18px; margin:0 0 8px; }
h2 { font-size:14px; margin:28px 0 8px; color:#9ec3ff; border-bottom:1px solid #2a2f3a; padding-bottom:4px; }
.meta { color:#7a8294; font-size:12px; }
.summary { display:grid; grid-template-columns:repeat(6, 1fr); gap:8px; margin:14px 0; }
.box { background:#1a1f29; border:1px solid #2a2f3a; border-radius:6px; padding:10px; }
.box .n { font-size:22px; font-weight:600; }
.box .lbl { color:#7a8294; font-size:11px; text-transform:uppercase; letter-spacing:0.04em; }
table.rows { width:100%; border-collapse:collapse; font-size:12px; }
table.rows th, table.rows td { padding:4px 8px; border-bottom:1px solid #1a1f29; text-align:left; }
table.rows th { color:#7a8294; font-weight:500; }
.idx { color:#7a8294; font-variant-numeric:tabular-nums; width:40px; }
.hint{ color:#7a8294; font-size:10px; margin-top:2px; }
.en  { font-family:ui-monospace,Menlo,monospace; color:#cdd6e3; }
.kr  { font-family:ui-monospace,Menlo,monospace; color:#cdd6e3; }
.status { font-size:10px; padding:2px 6px; border-radius:3px; display:inline-block; }
.translated     { background:#1d3a26; color:#7ee69a; }
.ASCII-different{ background:#2a1f3a; color:#c8a4ff; }
.mixed          { background:#3a2a14; color:#f0a06c; }
.placeholder    { background:#23262d; color:#8a93a5; }
.still-JP       { background:#382a14; color:#f0c46c; }
.unmapped       { background:#3a1a1a; color:#ff8a8a; }
details > summary { cursor:pointer; padding:8px 12px; background:#1a1f29; border:1px solid #2a2f3a;
                    border-radius:6px; font-weight:500; }
details[open] > summary { border-bottom-left-radius:0; border-bottom-right-radius:0; }
details > div { border:1px solid #2a2f3a; border-top:none; border-radius:0 0 6px 6px;
                background:#11141b; padding:0 12px 12px; }
.heatmap { display:grid; grid-template-columns:repeat(32, 1fr); gap:2px; max-width:900px; }
.cell { aspect-ratio:1; border-radius:2px; }
.cell.eq { background:#1d3a26; }
.cell.df { background:#3a1a1a; }
.cell.eq:hover, .cell.df:hover { outline:1px solid #fff; }
.legend { display:flex; gap:14px; margin:8px 0; font-size:11px; color:#7a8294; }
.legend span.swatch { display:inline-block; width:10px; height:10px; vertical-align:middle;
                      margin-right:4px; border-radius:2px; }
</style></head><body>""")
    html.append(f"<h1>LeafGreen ROM diff — EN US Rev 1 vs Korean 2024 patch</h1>")
    html.append(f"<div class='meta'>"
                f"EN: {escape(en_meta['name'])} · CRC32 <code>0x{en_meta['crc']:08X}</code> · {en_meta['size']:,} B<br>"
                f"KR: {escape(kr_meta['name'])} · CRC32 <code>0x{kr_meta['crc']:08X}</code> · {kr_meta['size']:,} B"
                f"</div>")

    html.append("<div class='summary'>")
    html.append(f"<div class='box'><div class='lbl'>Translated</div><div class='n' style='color:#7ee69a'>{grand_translated}</div></div>")
    html.append(f"<div class='box'><div class='lbl'>ASCII-different</div><div class='n' style='color:#c8a4ff'>{grand_asciidiff}</div></div>")
    html.append(f"<div class='box'><div class='lbl'>Placeholder (both)</div><div class='n' style='color:#8a93a5'>{grand_placeholder}</div></div>")
    html.append(f"<div class='box'><div class='lbl'>Still Japanese</div><div class='n' style='color:#f0c46c'>{grand_still_jp}</div></div>")
    html.append(f"<div class='box'><div class='lbl'>Unmapped KR codepoints</div><div class='n' style='color:#ff8a8a'>{grand_unmapped}</div></div>")
    html.append(f"<div class='box'><div class='lbl'>Binary identical (64 KB chunks)</div><div class='n'>{pct_identical:.1f}%</div></div>")
    html.append("</div>")
    html.append(f"<div class='meta'>{grand_total} name-table entries compared across {len(summary)} tables.</div>")

    html.append("<h2>Per-table pairing</h2>")
    for label, _b, _s, _n, _no, _nl in TABLES:
        stats = summary[label]
        rows = rows_by_table[label]
        total = sum(stats.values())
        # Status pills next to the table title
        pills = []
        for k in ("translated", "ASCII-different", "mixed", "placeholder", "still-JP", "unmapped"):
            if stats[k]:
                pills.append(f"<span class='status {k}'>{stats[k]} {k}</span>")
        html.append(f"<details><summary><b>{escape(label)}</b> &middot; "
                    f"{total} entries &middot; {' '.join(pills)}</summary><div>")
        html.append("<table class='rows'><thead><tr>"
                    "<th class='idx'>#</th><th>English</th><th>Korean</th><th>status</th></tr></thead><tbody>")
        for idx, en, kr, status, jp_dec in rows:
            jp_hint = ""
            if status in ("still-JP", "unmapped") and jp_dec:
                jp_hint = f"<div class='hint'>JP-decode: {escape(jp_dec)}</div>"
            html.append(f"<tr><td class='idx'>{idx}</td>"
                        f"<td class='en'>{escape(en) if en else '<span class=unmapped>—</span>'}</td>"
                        f"<td class='kr'>{escape(kr) if kr else '<span class=unmapped>—</span>'}{jp_hint}</td>"
                        f"<td><span class='status {status}'>{status}</span></td></tr>")
        html.append("</tbody></table></div></details>")

    html.append("<h2>Binary chunk heatmap (64 KB)</h2>")
    html.append("<div class='legend'>"
                "<div><span class='swatch' style='background:#1d3a26'></span>identical</div>"
                "<div><span class='swatch' style='background:#3a1a1a'></span>differs</div>"
                "<div>Each cell = 64 KB. Hover to see file offset.</div>"
                "</div>")
    html.append("<div class='heatmap'>")
    for off, sz, eh, kh, ok in chunks:
        cls = "eq" if ok else "df"
        title = f"0x{off:06X}-0x{off+sz-1:06X}  EN crc=0x{eh:08X}  KR crc=0x{kh:08X}  {'identical' if ok else 'differs'}"
        html.append(f"<div class='cell {cls}' title='{escape(title)}'></div>")
    html.append("</div>")

    # === Dialog ===
    html.append("<h2>Dialog corpus</h2>")
    html.append(f"<div class='meta'>Pointer-walked text records per ROM. Note: dialog "
                f"offsets do <i>not</i> align between the EN ROM and the JP-base + KR "
                f"patch — the patch stores text in different regions, so per-record "
                f"pairing isn't meaningful. The density rows below show <i>where</i> "
                f"each ROM keeps its dialog so the divergent regions in the binary "
                f"heatmap above are explained.</div>")
    html.append("<div class='summary' style='grid-template-columns:repeat(4, 1fr)'>")
    html.append(f"<div class='box'><div class='lbl'>EN records</div><div class='n'>{dialog['en_records']:,}</div></div>")
    html.append(f"<div class='box'><div class='lbl'>EN total chars</div><div class='n'>{dialog['en_chars']:,}</div></div>")
    html.append(f"<div class='box'><div class='lbl'>KR records</div><div class='n'>{dialog['kr_records']:,}</div></div>")
    html.append(f"<div class='box'><div class='lbl'>KR total chars</div><div class='n'>{dialog['kr_chars']:,}</div></div>")
    html.append("</div>")

    # Dialog density heatmap — record count per 64 KB chunk, log-scaled to
    # opacity so a single record stays visible while dense regions saturate.
    import math as _math
    en_max = max(dialog["en_density"]) or 1
    kr_max = max(dialog["kr_density"]) or 1
    html.append("<div class='meta' style='margin-top:8px'>EN dialog density (per 64 KB)</div>")
    html.append("<div class='heatmap'>")
    for off, density in enumerate(dialog["en_density"]):
        alpha = 0 if density == 0 else 0.15 + 0.85 * _math.log1p(density) / _math.log1p(en_max)
        title = f"0x{off*0x10000:06X}-0x{(off+1)*0x10000-1:06X}  EN records: {density}"
        html.append(f"<div class='cell' style='background:rgba(126,230,154,{alpha:.2f})' title='{escape(title)}'></div>")
    html.append("</div>")

    html.append("<div class='meta' style='margin-top:8px'>KR dialog density (per 64 KB)</div>")
    html.append("<div class='heatmap'>")
    for off, density in enumerate(dialog["kr_density"]):
        alpha = 0 if density == 0 else 0.15 + 0.85 * _math.log1p(density) / _math.log1p(kr_max)
        title = f"0x{off*0x10000:06X}-0x{(off+1)*0x10000-1:06X}  KR records: {density}"
        html.append(f"<div class='cell' style='background:rgba(158,195,255,{alpha:.2f})' title='{escape(title)}'></div>")
    html.append("</div>")

    html.append("</body></html>")
    return "".join(html)


def main() -> int:
    if not ROM_PATH_EN.exists():
        print(f"FAIL: EN ROM missing at {ROM_PATH_EN}", file=sys.stderr)
        return 1
    if not ROM_PATH.exists():
        print(f"FAIL: KR ROM missing at {ROM_PATH}", file=sys.stderr)
        return 1

    en_rom = ROM_PATH_EN.read_bytes()
    kr_rom = ROM_PATH.read_bytes()
    en_crc = zlib.crc32(en_rom)
    kr_crc = zlib.crc32(kr_rom)
    en_meta = {"name": ROM_PATH_EN.name, "crc": en_crc, "size": len(en_rom)}
    kr_meta = {"name": ROM_PATH.name, "crc": kr_crc, "size": len(kr_rom)}

    if en_crc != ROM_CRC32_EN:
        print(f"WARN: EN CRC32 0x{en_crc:08X} != expected 0x{ROM_CRC32_EN:08X}", file=sys.stderr)
    if kr_crc != ROM_CRC32_2024:
        print(f"WARN: KR CRC32 0x{kr_crc:08X} != expected 0x{ROM_CRC32_2024:08X}", file=sys.stderr)

    cp_map = json.loads(CODEPOINT_MAP_JSON.read_text(encoding="utf-8"))

    rows_by_table: dict[str, list] = {}
    summary: dict[str, dict[str, int]] = {}
    for label, base, stride, n, name_off, name_len in TABLES:
        rows = []
        stats = {"translated": 0, "ASCII-different": 0, "mixed": 0, "placeholder": 0, "still-JP": 0, "unmapped": 0}
        for idx in range(1, n):
            off = base + idx * stride + name_off
            en = decode_en(en_rom, off, name_len)
            raw_kr = kr_rom[off:off + name_len]
            kr, unk = decode_kr(kr_rom, off, name_len, cp_map)
            status = classify(en, kr, unk, raw_kr)
            stats[status] += 1
            jp_dec = jp_decode(raw_kr) if status in ("still-JP", "unmapped") else ""
            rows.append((idx, en, kr, status, jp_dec))
        rows_by_table[label] = rows
        summary[label] = stats

    chunks = chunk_diff(en_rom, kr_rom)
    en_rec, en_chars, en_density = load_dialog_density(CORPUS_EN_JSON, len(en_rom))
    kr_rec, kr_chars, kr_density = load_dialog_density(CORPUS_KR_JSON, len(kr_rom))
    dialog = {
        "en_records": en_rec, "en_chars": en_chars, "en_density": en_density,
        "kr_records": kr_rec, "kr_chars": kr_chars, "kr_density": kr_density,
    }

    html = render_html(en_meta, kr_meta, rows_by_table, summary, chunks, dialog)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT_HTML} ({len(html):,} bytes)")

    # Console summary
    print()
    print(f"{'Table':<24} {'translated':>11} {'ASCII-diff':>11} {'mixed':>6} {'placeholder':>12} {'still-JP':>9} {'unmapped':>9}")
    for label, stats in summary.items():
        print(f"{label:<24} {stats['translated']:>11} "
              f"{stats['ASCII-different']:>11} {stats['mixed']:>6} "
              f"{stats['placeholder']:>12} {stats['still-JP']:>9} {stats['unmapped']:>9}")

    identical = sum(sz for _, sz, _, _, ok in chunks if ok)
    total = sum(sz for _, sz, _, _, _ in chunks)
    print(f"\nBinary chunks (64 KB): {identical:,} / {total:,} bytes identical "
          f"({100.0 * identical / total:.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
