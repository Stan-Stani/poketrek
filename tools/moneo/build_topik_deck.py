#!/usr/bin/env python3
"""Build a TOPIK 1+2 vocab deck from corpus.ko.json.

Process:
  1. Load topik_glosses.json — hand-curated TOPIK 1/2 lemmas with English glosses.
  2. Mecab-lemmatize every record in corpus.ko.json.
  3. For each TOPIK lemma that appears in the corpus, pick the cleanest
     example sentence (shortest fluent sentence containing that lemma).
  4. Emit:
       app/src/main/assets/moneo/seed-vocab-ko-topik.json
       app/src/main/assets/moneo/sentences-ko-topik.json

Usage:  python3 tools/moneo/build_topik_deck.py
"""
from __future__ import annotations
import json
import re
from collections import defaultdict
from pathlib import Path

from mecab import MeCab  # type: ignore

ROOT = Path(__file__).resolve().parents[2]
GLOSSES_PATH = ROOT / "tools/moneo/topik_glosses.json"
CORPUS_PATH = ROOT / "app/src/main/assets/moneo/corpus.ko.json"
OUT_VOCAB = ROOT / "app/src/main/assets/moneo/seed-vocab-ko-topik.json"
OUT_SENTS = ROOT / "app/src/main/assets/moneo/sentences-ko-topik.json"

SOURCE_TAG = "topik-v1"
AREA_ID = "topik_basic"

SENT_SPLIT = re.compile(r"[\.!\?。…]+|\n+")
HANGUL_RE = re.compile(r"[가-힣]")


def is_hangul(c: str) -> bool:
    return "가" <= c <= "힣"


# Reuse the romanization from mine_vocab.py to keep card display consistent.
INITIALS = ["g", "kk", "n", "d", "tt", "r", "m", "b", "pp", "s", "ss", "", "j", "jj", "ch", "k", "t", "p", "h"]
VOWELS = ["a", "ae", "ya", "yae", "eo", "e", "yeo", "ye", "o", "wa", "wae", "oe", "yo", "u", "wo", "we", "wi", "yu", "eu", "ui", "i"]
FINALS = ["", "g", "kk", "gs", "n", "nj", "nh", "d", "l", "lg", "lm", "lb", "ls", "lt", "lp", "lh", "m", "b", "bs", "s", "ss", "ng", "j", "ch", "k", "t", "p", "h"]


def romanize_syllable(c: str) -> str:
    if not is_hangul(c):
        return c
    code = ord(c) - 0xAC00
    i, m, f = code // 588, (code % 588) // 28, code % 28
    return INITIALS[i] + VOWELS[m] + FINALS[f]


def romanize(text: str) -> str:
    out = []
    for c in text:
        if is_hangul(c):
            out.append(romanize_syllable(c))
            out.append("-")
        else:
            if out and out[-1] == "-":
                out.pop()
            out.append(c)
    if out and out[-1] == "-":
        out.pop()
    return "".join(out).replace("--", "-").replace(" -", " ").replace("- ", " ").strip("-")


def lemmas_in(sentence: str, m: MeCab) -> set[str]:
    """All TOPIK-comparable lemmas this sentence emits."""
    out: set[str] = set()
    for tok in m.parse(sentence):
        f = tok.feature
        pos = f.pos
        if f.type == "Inflect" and f.expression:
            for piece in f.expression.split("+"):
                parts = piece.split("/")
                if len(parts) >= 2 and parts[1] in ("VV", "VA"):
                    out.add(parts[0] + "다"); break
                if len(parts) >= 2 and parts[1] in ("NNG", "NNP"):
                    out.add(parts[0]); break
        elif pos in ("VV", "VA"):
            out.add(tok.surface + "다")
        elif pos in ("NNG", "NNP", "MAG"):
            out.add(tok.surface)
    return out


def main() -> int:
    glosses = json.loads(GLOSSES_PATH.read_text(encoding="utf-8"))["glosses"]
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    m = MeCab()

    # For each topik lemma, gather candidate (rec_id, sentence, length) tuples.
    candidates: dict[str, list[tuple]] = defaultdict(list)

    for rec in corpus["records"]:
        text = rec["text"]
        for sentence in SENT_SPLIT.split(text):
            sentence = sentence.strip()
            if not sentence:
                continue
            han_count = sum(1 for c in sentence if is_hangul(c))
            if han_count < 4 or han_count > 50:
                continue
            han_ratio = han_count / max(len(sentence), 1)
            if han_ratio < 0.7:
                continue
            lems = lemmas_in(sentence, m)
            hits = lems & glosses.keys()
            if not hits:
                continue
            for lemma in hits:
                candidates[lemma].append((rec["id"], sentence, len(sentence)))

    # Pick best example per lemma: shortest sentence that contains the lemma.
    vocab_entries = []
    sent_entries = []
    pos_for = {}
    for lemma in sorted(glosses.keys()):
        if lemma == "_comment":
            continue
        if lemma not in candidates:
            continue
        candidates[lemma].sort(key=lambda c: c[2])
        rec_id, sentence, _ = candidates[lemma][0]
        gloss = glosses[lemma]
        # Heuristic POS from lemma shape — same buckets the runtime expects.
        if lemma.endswith("다"):
            pos = "verb/adj"
        else:
            pos = "noun/adv"
        pos_for[lemma] = pos
        vocab_entries.append({
            "korean": lemma,
            "romanization": romanize(lemma),
            "gloss": gloss,
            "partOfSpeech": pos,
            "areaId": AREA_ID,
            "frequency": len(candidates[lemma]),
        })
        sent_entries.append({
            "vocabId": f"{SOURCE_TAG}:{lemma}",
            "korean": sentence,
            "romanization": romanize(sentence),
            "gloss": "(TOPIK 1/2 example from ROM)",
            "targetForm": lemma,
            "areaId": AREA_ID,
            "source": f"rom-rec{rec_id}",
        })

    OUT_VOCAB.write_text(json.dumps({
        "version": 1,
        "source": SOURCE_TAG,
        "areaId": AREA_ID,
        "notes": (
            "TOPIK Level 1+2 vocabulary that occurs in the Korean LeafGreen ROM "
            "dialogue corpus. Hand-glossed from julienshim/combined_korean_vocabulary_list."
        ),
        "entries": vocab_entries,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_SENTS.write_text(json.dumps({
        "version": 1,
        "source": SOURCE_TAG,
        "entries": sent_entries,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"vocab: {len(vocab_entries)} entries -> {OUT_VOCAB}")
    print(f"sents: {len(sent_entries)} entries -> {OUT_SENTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
