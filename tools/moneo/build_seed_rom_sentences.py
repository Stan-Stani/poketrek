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


def is_clean(s: str, *, strict: bool = True) -> bool:
    if not s: return False
    # no leftover unknown markers
    if "<" in s or "[" in s: return False
    # mostly Korean
    han = sum(1 for c in s if 0xAC00 <= ord(c) <= 0xD7A3)
    if strict:
        return han >= 3 and han / max(1, len(s)) >= 0.4
    # Loose mode for rare-lemma fallback: just require some Korean content
    return han >= 3


def search_terms(word: str) -> list[str]:
    """Yield search terms for a seed word: the dictionary form plus likely
    conjugation stems for verbs/adjectives ending in 다."""
    terms = [word]
    if word.endswith("다") and len(word) >= 2:
        stem = word[:-1]
        # Search by stem; we'll match any sentence containing it followed by a
        # Korean character (conjugation/particle). This covers 싸우지/싸워/싸웠다 etc.
        terms.append(stem)
    return terms


def find_example(word: str, records: list, lemma_info: dict | None):
    """Return (record, sentence, speaker, target_form) for best example, or None."""
    rec_ids_pref = (lemma_info or {}).get("rec_ids", [])
    terms = search_terms(word)

    candidates: list[tuple[int, dict, str, str | None, str]] = []
    for r in records:
        text = r.get("text", "")
        # Quick reject if no term matches
        if not any(t in text for t in terms): continue
        # Split into sentence-ish chunks
        chunks = re.split(r"[.!?。]| \n|·{4,}", text)
        for chunk in chunks:
            c = clean_sentence(chunk)
            # Identify which term hits and capture the surface form
            target_form = None
            for t in terms:
                idx = c.find(t)
                if idx < 0: continue
                # For stem search, ensure followed by a Korean syllable
                # (otherwise it's a coincidental substring inside a different word)
                if t != word:  # stem mode
                    tail_start = idx + len(t)
                    if tail_start >= len(c): continue
                    next_ch = c[tail_start]
                    if not (0xAC00 <= ord(next_ch) <= 0xD7A3): continue
                    # Grab 1-3 trailing Korean chars as the surface form
                    j = tail_start
                    while j < len(c) and j < tail_start + 3 and 0xAC00 <= ord(c[j]) <= 0xD7A3:
                        j += 1
                    target_form = c[idx:j]
                else:
                    target_form = word
                break
            if target_form is None: continue
            if not (8 <= len(c) <= 90): continue
            if not is_clean(c, strict=True): continue
            speaker = None
            for sp in KNOWN_SPEAKERS:
                if sp in c[:20] or sp in text[:30]:
                    speaker = sp; break
            score = 0
            if r["id"] in rec_ids_pref: score += 100
            if speaker == "오박사": score += 20
            elif speaker: score += 10
            if 12 <= len(c) <= 50: score += 5
            # Slightly prefer the dictionary form over a conjugation
            if target_form == word: score += 3
            candidates.append((score, r, c, speaker, target_form))

    if candidates:
        candidates.sort(key=lambda x: -x[0])
        _, rec, sent, speaker, target_form = candidates[0]
        return rec, sent, speaker, target_form

    # Fallback: rare lemma. Try again with loose cleanliness + shorter min length,
    # and accept the longest cleanish chunk that contains the surface form.
    for r in records:
        text = r.get("text", "")
        if not any(t in text for t in terms): continue
        # Don't pre-chunk; take a 50-char window around the hit
        for t in terms:
            idx = text.find(t)
            if idx < 0: continue
            start = max(0, idx - 25)
            end = min(len(text), idx + len(t) + 30)
            window = clean_sentence(text[start:end])
            if not (6 <= len(window) <= 90): continue
            if not is_clean(window, strict=False): continue
            target_form = t
            if t != word:
                # Capture conjugation if present
                hit_idx = window.find(t)
                if hit_idx >= 0:
                    j = hit_idx + len(t)
                    while j < len(window) and j < hit_idx + len(t) + 3 \
                            and 0xAC00 <= ord(window[j]) <= 0xD7A3:
                        j += 1
                    target_form = window[hit_idx:j]
            return r, window, None, target_form
    return None


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
        rec, sent, speaker, target_form = hit
        entry = {
            "vocabId": f"seed-v1:{word}",
            "korean": sent,
            "gloss": f"({gloss})" if gloss else "",
            "areaId": (info or {}).get("first_area", "rom_mined"),
            "source": f"rom-rec{rec['id']}",
        }
        # Pin the conjugated surface form so the validator's substring check
        # uses the actual form that appears in the sentence (e.g. "싸우고"),
        # not the dictionary form ("싸우다") which the sentence won't contain.
        if target_form and target_form != word:
            entry["targetForm"] = target_form
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
