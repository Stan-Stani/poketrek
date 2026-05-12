#!/usr/bin/env python3
"""Re-extract sentences-ko-rom.json from the 2024 corpus.

For each word in seed-vocab-ko.json, finds a clean short Korean
sentence in the 2024 corpus that contains it. Prefers dialog
that mentions known NPC speakers (오박사 = Oak, mom, etc.) and
falls back to anywhere in the corpus.

Replaces the prior 2010-vintage file (30 hand-curated Oak sentences
using 오키드 instead of the modern 오박사 localization).
"""
from __future__ import annotations
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ASSETS = ROOT / "app/src/main/assets/moneo"

CORPUS = ASSETS / "corpus.ko.json"
SEED   = ASSETS / "seed-vocab-ko.json"
OUT    = ASSETS / "sentences-ko-rom.json"
LEMMA  = HERE / "lemma_area_index.json"

# 2024 Korean speakers we can attribute lines to. (한자/외래어 names appear in
# overworld dialog; tag a sentence's speaker if the text begins with one.)
KNOWN_SPEAKERS = ["오박사", "엄마", "{var:01}", "{var:02}"]


def clean_sentence(s: str) -> str:
    """Strip filler dots, collapse whitespace, drop control markers."""
    s = re.sub(r"\[[0-9A-F]{4}\]", "", s)  # [3FFF] etc.
    s = s.replace("·", " ").replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def is_clean(s: str) -> bool:
    if not s: return False
    # no leftover unknown markers
    if "<" in s or "[" in s: return False
    # mostly Korean
    han = sum(1 for c in s if 0xAC00 <= ord(c) <= 0xD7A3)
    return han >= 3 and han / max(1, len(s)) >= 0.4


def find_example(word: str, records: list, lemma_info: dict | None):
    """Return (record, sentence, speaker) for the best example, or None."""
    # First pass: look in lemma's tracked rec_ids
    rec_ids_pref = (lemma_info or {}).get("rec_ids", [])
    rec_by_id = {r["id"]: r for r in records}

    candidates: list[tuple[int, dict, str, str | None]] = []  # (score, rec, sentence, speaker)
    for r in records:
        text = r.get("text", "")
        if word not in text: continue
        # Split into sentence-ish chunks on common Korean clause boundaries
        chunks = re.split(r"[.!?。]| \n|·{4,}", text)
        for chunk in chunks:
            c = clean_sentence(chunk)
            if word not in c: continue
            if not (8 <= len(c) <= 90): continue
            if not is_clean(c): continue
            speaker = None
            for sp in KNOWN_SPEAKERS:
                if sp in c[:20] or sp in text[:30]:
                    speaker = sp; break
            score = 0
            if r["id"] in rec_ids_pref: score += 100
            if speaker == "오박사": score += 20
            elif speaker: score += 10
            if 12 <= len(c) <= 50: score += 5
            candidates.append((score, r, c, speaker))

    if not candidates: return None
    candidates.sort(key=lambda x: -x[0])
    _, rec, sent, speaker = candidates[0]
    return rec, sent, speaker


def main():
    corpus = json.loads(CORPUS.read_text())["records"]
    seed = json.loads(SEED.read_text())["entries"]
    lemma_idx = json.loads(LEMMA.read_text())["lemmas"]

    out_entries: list[dict] = []
    matched, missed = 0, 0
    missing_words: list[str] = []
    for s in seed:
        word = s["korean"]
        gloss = s.get("gloss", "")
        info = lemma_idx.get(word)
        hit = find_example(word, corpus, info)
        if not hit:
            missed += 1
            missing_words.append(word)
            continue
        rec, sent, speaker = hit
        entry = {
            "vocabId": f"seed-v1:{word}",
            "korean": sent,
            "gloss": f"({gloss})" if gloss else "",
            "areaId": (info or {}).get("first_area", "rom_mined"),
            "source": f"rom-rec{rec['id']}",
        }
        if speaker:
            entry["speaker"] = speaker
        if info and info.get("source_types"):
            entry["sourceTypes"] = info["source_types"]
            entry["primarySourceType"] = info.get("primary_source_type", "")
        out_entries.append(entry)
        matched += 1

    out = {
        "version": 2,
        "sourceTag": "rom-v2",
        "notes": (
            f"Sentences extracted verbatim from corpus.ko.json (2024 "
            f"Korean LeafGreen decode). Each entry's `source` field references "
            f"a record id in that corpus. Replaces the 2010-vintage file "
            f"which used 오키드/도장 (Japanese-romanized localization) "
            f"instead of 오박사/체육관."
        ),
        "entries": out_entries,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"wrote {OUT.relative_to(ROOT)}: {matched} matched, {missed} no-match")
    if missing_words:
        print(f"  no-match words ({len(missing_words)}): {missing_words[:15]}...")


if __name__ == "__main__":
    main()
