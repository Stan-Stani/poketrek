#!/usr/bin/env python3
"""Apply hand-curated glosses to the mecab-mined vocab + sentence assets.

Reads tools/moneo/manual_glosses.json and rewrites
  app/src/main/assets/moneo/seed-vocab-ko-mined.json
  app/src/main/assets/moneo/sentences-ko-mined.json

Entries whose Korean key is present in manual_glosses.json get the curated
gloss; entries absent from manual_glosses.json are dropped (they are
treated as Mecab over-analysis of kana-romanized fragments). The same
filter is applied to the sentence asset to keep vocabId references valid.

Usage:  python3 tools/moneo/apply_glosses.py
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GLOSSES = ROOT / "tools/moneo/manual_glosses.json"
VOCAB = ROOT / "app/src/main/assets/moneo/seed-vocab-ko-mined.json"
SENTS = ROOT / "app/src/main/assets/moneo/sentences-ko-mined.json"


def main() -> int:
    glosses = json.loads(GLOSSES.read_text(encoding="utf-8"))["glosses"]

    vocab_doc = json.loads(VOCAB.read_text(encoding="utf-8"))
    entries_in = vocab_doc["entries"]
    entries_out = []
    kept_ids: set[str] = set()
    for e in entries_in:
        ko = e["korean"]
        if ko not in glosses:
            continue
        e["gloss"] = glosses[ko]
        entries_out.append(e)
        # Reconstruct the same vocabId the miner emitted so we can filter
        # sentences in lockstep.
        kept_ids.add(f"rom-mine-v3:{ko}")

    vocab_doc["entries"] = entries_out
    vocab_doc.setdefault("notes", "")
    vocab_doc["notes"] = (
        f"Mecab-ko mined + hand-glossed. {len(entries_out)} cards "
        f"(of {len(entries_in)} raw mined; remainder were Mecab "
        f"over-analysis of kana-romanized fragments)."
    )
    VOCAB.write_text(
        json.dumps(vocab_doc, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"vocab: {len(entries_in)} → {len(entries_out)} entries")

    sent_doc = json.loads(SENTS.read_text(encoding="utf-8"))
    sents_in = sent_doc["entries"]
    sents_out = [s for s in sents_in if s.get("vocabId") in kept_ids]
    sent_doc["entries"] = sents_out
    SENTS.write_text(
        json.dumps(sent_doc, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"sentences: {len(sents_in)} → {len(sents_out)} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
