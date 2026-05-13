#!/usr/bin/env python3
"""Rebuild every bundled seed-vocab-ko-*.json so each entry carries:

  - `gloss`  : the single primary English headword (no semicolons)
  - `senses` : optional list of secondary senses

Priority for the primary `gloss`:
  1. ROM-table English from `name_tables_en.json` when the entry's
     `source` field tags it (e.g. `gMoveNames[1]` → "Pound").
  2. `dialog_map_en.json` override (curated by hand for non-table lemmas).
  3. The first sense of the existing `gloss` (paren-aware split on `;`).

Anything dropped from the primary slot lands in `senses[]`, deduped and
never duplicating the primary itself.

Idempotent — running twice produces no further changes. Run as part of
the RUNBOOK after `apply_glosses_nondestructive.py`.
"""
from __future__ import annotations
import json
import re
import sys
from datetime import date
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
ROOT = THIS_DIR.parents[1]

NAME_TABLES = THIS_DIR / "name_tables_en.json"
DIALOG_MAP  = THIS_DIR / "dialog_map_en.json"
ASSETS_DIR  = ROOT / "app/src/main/assets/moneo"
ASSETS = [
    ASSETS_DIR / "seed-vocab-ko-mined.json",
    ASSETS_DIR / "seed-vocab-ko-topik.json",
    ASSETS_DIR / "seed-vocab-ko-species.json",
    ASSETS_DIR / "seed-vocab-ko-etymology.json",
]

# Strip these parenthesised annotations from old glosses when ROM-table
# canonical wins. They're carry-overs from build_name_table_decks.py
# (KR ROM); the EN ROM string is itself the headword.
_ANNOTATION_RE = re.compile(r"\s*\((?:move|Pok[eé]mon|ability|item|species)\)\s*$", re.IGNORECASE)


def split_senses(s: str) -> list[str]:
    """Paren-aware split on ';'. Etymology entries embed semicolons inside
    parentheses ("(only in 날쌩마; ...)"); a naive split mangles them.
    """
    out: list[str] = []
    depth = 0
    cur: list[str] = []
    for ch in s:
        if ch in "([{":
            depth += 1
            cur.append(ch)
        elif ch in ")]}":
            depth = max(0, depth - 1)
            cur.append(ch)
        elif ch == ";" and depth == 0:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    tail = "".join(cur).strip()
    if tail:
        out.append(tail)
    return [s for s in out if s]


SOURCE_TABLE_RE = re.compile(r"^(gMoveNames|gAbilityNames|gSpeciesNames|gItems|gPokedexEntries\.category)\[(\d+)\]$")


def rom_table_gloss(source: str | None, tables: dict[str, dict[str, str]]) -> str | None:
    if not source:
        return None
    m = SOURCE_TABLE_RE.match(source)
    if not m:
        return None
    return tables.get(m.group(1), {}).get(m.group(2))


def restructure_entry(e: dict, tables: dict[str, dict[str, str]],
                      dialog_map: dict[str, dict]) -> tuple[bool, str]:
    """Mutate `e` in place. Returns (changed, reason)."""
    ko = e.get("korean")
    old_gloss = (e.get("gloss") or "").strip()
    old_senses = list(e.get("senses") or [])

    # ROM-table canonical wins for ROM-anchored entries. The same Korean
    # surface can be both a move name and a common noun (방어 = the move
    # Protect at gMoveNames[182] AND the stat Defense in dialog), and the
    # source-tagged card is *always* about the move. dialog_map only
    # applies to dialog/text-mined lemmas.
    rom_gloss = rom_table_gloss(e.get("source"), tables)
    if rom_gloss:
        primary = rom_gloss
        # Discard the old gloss entirely for ROM-table entries: stale
        # PokeAPI mappings sometimes pointed at the wrong species, and
        # carrying those into senses would teach a wrong pair next to
        # the right one.
        leftover_pool = []
        reason = "rom-table"
    elif ko and ko in dialog_map:
        m = dialog_map[ko]
        primary = m["gloss"].strip()
        leftover_pool = list(m.get("senses", []))
        reason = "dialog-map"
    else:
        senses = split_senses(old_gloss)
        if not senses:
            return False, "empty"
        primary = senses[0]
        leftover_pool = senses[1:] + old_senses
        reason = "split" if len(senses) > 1 or old_senses else "noop"

    seen: set[str] = {primary}
    senses_out: list[str] = []
    for s in leftover_pool:
        s = s.strip()
        if not s or s in seen:
            continue
        seen.add(s)
        senses_out.append(s)

    new_gloss = primary
    new_senses = senses_out

    changed = (new_gloss != old_gloss) or (new_senses != old_senses)
    e["gloss"] = new_gloss
    if new_senses:
        e["senses"] = new_senses
    elif "senses" in e:
        # Don't keep an empty senses field
        del e["senses"]
    return changed, reason


def process_file(path: Path, tables: dict, dialog_map: dict) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    entries = doc.get("entries") or []
    stats = {"rom-table": 0, "dialog-map": 0, "split": 0, "noop": 0, "empty": 0}
    changed_count = 0
    for e in entries:
        changed, reason = restructure_entry(e, tables, dialog_map)
        stats[reason] = stats.get(reason, 0) + 1
        if changed:
            changed_count += 1

    notes = doc.get("notes", [])
    if not isinstance(notes, list):
        notes = [notes] if notes else []
    notes.append(
        f"restructure_glosses {date.today().isoformat()}: "
        f"{changed_count} entries updated; "
        f"rom-table={stats['rom-table']} dialog-map={stats['dialog-map']} "
        f"split={stats['split']} noop={stats['noop']}"
    )
    doc["notes"] = notes
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"  {path.name}: {changed_count}/{len(entries)} changed  {stats}")
    return stats


def main() -> int:
    if not NAME_TABLES.exists():
        print(f"FAIL: {NAME_TABLES} missing — run build_name_table_decks_en.py first.",
              file=sys.stderr)
        return 1
    tables_doc = json.loads(NAME_TABLES.read_text(encoding="utf-8"))
    tables = tables_doc["tables"]
    dialog_map_doc = json.loads(DIALOG_MAP.read_text(encoding="utf-8")) if DIALOG_MAP.exists() else {"entries": {}}
    dialog_map = dialog_map_doc.get("entries", {})

    print(f"name tables: {sum(len(v) for v in tables.values())} entries across "
          f"{len(tables)} tables")
    print(f"dialog map:  {len(dialog_map)} curated lemmas")
    print()

    for path in ASSETS:
        if not path.exists():
            print(f"  {path.name}: MISSING — skipped")
            continue
        process_file(path, tables, dialog_map)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
