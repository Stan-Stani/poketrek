#!/usr/bin/env python3
"""Apply hand-curated glosses from manual_glosses.json to the mined deck
and matching sentences WITHOUT dropping unglossed entries.

The legacy tools/moneo/apply_glosses.py was destructive: it removed any
entry whose Korean key wasn't in manual_glosses.json (designed for the
old pipeline where mecab over-mined kana-romaji fragments). After the
2024 corpus regen, mined entries are real Korean — we want to keep them
and just upgrade the gloss when an authoritative one is available.

This script:
  - Reads manual_glosses.json
  - For each entry in seed-vocab-ko-mined.json: if korean in glosses,
    overwrite the gloss; else keep the existing gloss (placeholder or
    name-tag).
  - Doesn't touch sentences (they don't carry a gloss field that needs
    updating; the vocab card is what reviewers see).
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GLOSSES = ROOT / "tools/moneo/manual_glosses.json"
VOCAB = ROOT / "app/src/main/assets/moneo/seed-vocab-ko-mined.json"


def main() -> int:
    glosses = json.loads(GLOSSES.read_text(encoding="utf-8"))["glosses"]
    vocab_doc = json.loads(VOCAB.read_text(encoding="utf-8"))
    entries = vocab_doc["entries"]

    upgraded = 0
    placeholder_kept = 0
    already_good = 0
    for e in entries:
        ko = e.get("korean")
        if not ko: continue
        cur = e.get("gloss") or ""
        # Apply gloss when available
        if ko in glosses:
            if cur != glosses[ko]:
                e["gloss"] = glosses[ko]
                upgraded += 1
            else:
                already_good += 1
        elif cur.startswith("(unglossed") or cur.startswith("(surfaced") or cur.startswith("(undecoded"):
            placeholder_kept += 1

    notes = vocab_doc.get("notes", [])
    if not isinstance(notes, list): notes = [notes] if notes else []
    notes.append(
        f"apply_glosses_nondestructive: upgraded {upgraded} glosses from "
        f"manual_glosses.json ({len(glosses)} curated translations). "
        f"{placeholder_kept} cards remain on placeholder glosses (not yet "
        f"hand-translated)."
    )
    vocab_doc["notes"] = notes
    VOCAB.write_text(json.dumps(vocab_doc, ensure_ascii=False, indent=1))
    print(f"  upgraded: {upgraded}")
    print(f"  already correct: {already_good}")
    print(f"  placeholder kept: {placeholder_kept}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
