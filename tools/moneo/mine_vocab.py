#!/usr/bin/env python3
"""
Mine vocab + sentences from corpus.ko.json.

Reads the Phase-2 ROM rip and produces two assets:
  app/src/main/assets/moneo/seed-vocab-ko-mined.json
  app/src/main/assets/moneo/sentences-ko-mined.json

Pipeline:
  1. Compute corpus-wide character frequency. Drop "garbled" records
     (those whose Hangul is mostly rare characters — these come from
     low-coverage charmap regions and aren't real Korean).
  2. For each fluent record, split on particle suffixes AND on common
     verb endings — the ROM corpus has minimal word-spacing, so this
     synthetic spacing is what lets us recover word-shaped tokens.
  3. Deconjugate verb/adjective surface forms back to a `…다` lemma so
     inflection (가요/갔어요/가는) doesn't hide the same root.
  4. Count lemma frequency. Filter:
       - already in seed-vocab-ko.json (skip dupes)
       - token length 2-4 syllables
       - frequency >= --threshold
  5. Pick the cleanest example sentence per lemma; emit JSON.

Usage:
  python3 tools/moneo/mine_vocab.py --threshold 15 [--limit N] [--dry-run]
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "app/src/main/assets/moneo/corpus.ko.json"
SEED = ROOT / "app/src/main/assets/moneo/seed-vocab-ko.json"
OUT_VOCAB = ROOT / "app/src/main/assets/moneo/seed-vocab-ko-mined.json"
OUT_SENTS = ROOT / "app/src/main/assets/moneo/sentences-ko-mined.json"

SOURCE_TAG = "rom-mine-v2"
AREA_ID = "rom_mined"

# ---------------------------------------------------------------------------
# Mecab-ko (preferred) — proper Korean morphological analysis.
# Falls back to the regex-based heuristic below when the package isn't
# installed, so the script remains runnable without the venv.
# ---------------------------------------------------------------------------

try:
    from mecab import MeCab as _MeCabImpl  # type: ignore
    _MECAB = _MeCabImpl()
except Exception:  # ImportError or dictionary-load errors
    _MECAB = None


# Mecab-ko POS tags we want as content lemmas.
_LEMMA_POS = {
    "NNG": "noun",       # general noun
    "NNP": "noun",       # proper noun
    "VV":  "verb",       # verb stem
    "VA":  "adjective",  # descriptive verb (adjective)
    "MAG": "adverb",     # adverb
}


def mecab_lemmatize(sentence: str) -> list[tuple[str, str, str]]:
    """Tokenize *sentence* via mecab-ko and return [(lemma, pos, surface)].

    For inflected verbs/adjectives (type='Inflect') the lemma is reconstructed
    from the first verb/adjective morpheme of `expression`, with 다 appended,
    e.g. "강해져" → ("강해지다", "verb", "강해져"). Particles, endings, and
    punctuation are dropped.
    """
    assert _MECAB is not None
    out: list[tuple[str, str, str]] = []
    for tok in _MECAB.parse(sentence):
        f = tok.feature
        pos = f.pos
        if f.type == "Inflect" and f.expression:
            # expression looks like "강하/VA/*+아/EC/*+지/VX/*+어/EC/*"
            # — find the first VV/VA morpheme to recover the dict form.
            chosen = None
            for piece in f.expression.split("+"):
                parts = piece.split("/")
                if len(parts) >= 2 and parts[1] in ("VV", "VA"):
                    chosen = (parts[0] + "다", _LEMMA_POS[parts[1]])
                    break
                if len(parts) >= 2 and parts[1] in ("NNG", "NNP"):
                    chosen = (parts[0], _LEMMA_POS[parts[1]])
                    break
            if chosen is not None:
                out.append((chosen[0], chosen[1], tok.surface))
            continue
        # Simple POS — keep as-is for nouns/adverbs, append 다 for verb/adj
        # stems so the flashcard shows the dictionary form.
        if pos in ("VV", "VA"):
            out.append((tok.surface + "다", _LEMMA_POS[pos], tok.surface))
        elif pos in _LEMMA_POS:
            out.append((tok.surface, _LEMMA_POS[pos], tok.surface))
    return out


# ---------------------------------------------------------------------------
# Korean morphology (legacy regex-based fallback)
# ---------------------------------------------------------------------------

# Particles split AFTER (so "포켓몬을 잡다" surfaces "포켓몬을" + "잡다",
# then particle-strip recovers "포켓몬"). Order longest-first.
PARTICLES = sorted(
    [
        "에서는", "에서도", "이라고", "이라는", "이라도",
        "에게서", "한테서", "에서", "으로", "에게", "한테",
        "부터", "까지", "마다", "처럼",
        "과", "와", "도", "만", "의", "에", "로",
        "은", "는", "이", "가", "을", "를",
    ],
    key=len,
    reverse=True,
)

# Verb/adj endings split BEFORE (so "포켓몬을잡았어요" → "포켓몬을 잡았어요",
# then deconjugate strips 았어요 → 잡 → 잡다). Order longest-first.
ENDINGS = sorted(
    [
        "었습니다", "았습니다", "였습니다",
        "었어요", "았어요", "였어요",
        "어집니다", "아집니다", "어진다", "아진다",
        "었어", "았어", "였어",
        "었다", "았다", "였다",
        "셨습니다", "셨어요", "시었어요",
        "습니다", "습니까", "ㅂ니다", "ㅂ니까",
        "어요", "아요", "여요",
        "는다", "ㄴ다",
        "으면", "으면서", "면서",
        "지만", "는데", "은데",
        "아서", "어서", "여서",
        "고서", "면",
        "었", "았", "였",
    ],
    key=len,
    reverse=True,
)

# Hada-verb collapses (해 = 하 + 어)
HADA_FORMS = sorted(
    [
        ("했습니다", "하다"), ("했어요", "하다"), ("했어", "하다"), ("했다", "하다"),
        ("합니다", "하다"), ("해요", "하다"), ("한다", "하다"),
    ],
    key=lambda kv: len(kv[0]),
    reverse=True,
)

VAR_RE = re.compile(r"\{var:[^}]+\}")
ANGLE_RE = re.compile(r"⟨[^⟩]+⟩")
NOISE_CHARS_RE = re.compile(r"[·äZ]")
SENT_SPLIT = re.compile(r"[。!?\n]+")
NON_HANGUL_RE = re.compile(r"[^가-힣]+")

STOPWORDS = {
    # bare deictics already in seed
    "그", "이", "저", "것", "수", "때", "일", "거", "줄", "데",
    "들", "님", "씨", "나", "너",
    # Japanese-rendered ROM debris (very common, not useful Korean)
    "테이루", "타이", "테이", "마스", "데스", "이루",
    "토우", "코토", "이마스", "이루마",
    # too generic
    "이다",
}

# Substrings that betray Japanese-romanized-in-Hangul text. Many ROM strings
# weren't translated and got phonetically transliterated; we don't want those
# polluting the Korean vocab list.
JAPANESE_ROM_PATTERNS = [
    "이루", "란테", "란타", "마스", "데스", "이마스", "테이루",
    "베사이", "쿠베사", "쿠베", "노데", "토이우", "츠우", "이타이",
    "츠나", "츠노", "츠시", "츠즈", "이쿠",  "에루", "라레",
    "사이", "데이", "데키", "타리", "마세", "이키", "유우", "료우",
    "미타이", "테쿠", "쿠레", "샤이", "마이", "와루", "베쿠",
    "이마", "나이", "오쿠", "으우",
]

# Hangul syllables that the ROM uses to render Japanese kana phonetically.
# A 2-syllable noun consisting entirely of these (with no final consonant)
# is overwhelmingly a fan-translation Pokémon move/ability/item name, not
# real Korean — drop it. Native Korean 2-syl words sometimes share this
# shape (e.g. 가지, 모기) but those will pass the threshold filter via
# repetition in real dialogue contexts and can be hand-curated later.
KANA_SHAPE_SYLLABLES = set(
    "아이우에오"
    "카키쿠케코가기구게고"
    "사시스세소자지즈제조"
    "타치츠테토다디두데도"
    "나니누네노"
    "하히후헤호바비부베보파피푸페포"
    "마미무메모"
    "야유요"
    "라리루레로"
    "와데"
)


def is_kana_shape_token(token: str) -> bool:
    """True if every syllable in *token* is open-syllable (no batchim) and
    drawn from the kana-rendering subset above. Length-2 tokens matching
    this are almost always Japanese romanization in this corpus."""
    if len(token) != 2:
        return False
    for c in token:
        code = ord(c) - 0xAC00
        if code < 0 or code >= 0xD7A4 - 0xAC00:
            return False
        if code % 28 != 0:  # has batchim
            return False
        if c not in KANA_SHAPE_SYLLABLES:
            return False
    return True

# Sentence must end with a plausible Korean copula/verb-ending. Real Korean
# sentences end in 다/요/까/자/네/지/면/서/고/며/든 etc.; Japanese-rendered
# lines tend to end in -이루, -란타, -이타, -마스 (caught by JP-pattern check).
KOREAN_ENDINGS = "다요까자네지면서고며든"
KOREAN_END_RE = re.compile(rf"[가-힣][{KOREAN_ENDINGS}](?:[\?!]|$)")

# A real Korean sentence usually contains at least one nominal particle.
# Japanese-rendered lines tend not to.
PARTICLE_PROBE_RE = re.compile(r"[가-힣](?:이|가|은|는|을|를|의|에|로|와|과|도|만|에서|에게)(?=[가-힣]|\s|$)")


def is_hangul(c: str) -> bool:
    return "가" <= c <= "힣"


def is_vowel_only_syllable(c: str) -> bool:
    """A precomposed Hangul syllable with the silent ㅇ initial AND no jongseong
    (i.e., pure vowel: 아 어 오 우 이 에 야 여 요 유 etc.). Strings made
    entirely of these are almost always kana-romanized Japanese debris in this
    corpus, not real Korean."""
    code = ord(c)
    if not (0xAC00 <= code <= 0xD7A3):
        return False
    idx = code - 0xAC00
    initial = idx // 588          # 11 == ㅇ (silent placeholder)
    jongseong = idx % 28          # 0 == no batchim
    return initial == 11 and jongseong == 0


def is_phonetic_noise(token: str) -> bool:
    """Reject tokens whose every character is a vowel-only syllable."""
    if not token:
        return False
    return all(is_vowel_only_syllable(c) for c in token)


def has_no_batchim(token: str) -> bool:
    """True if no syllable in the token carries a final consonant. Real Korean
    of length ≥3 nearly always has at least one batchim (받침); strings without
    one are almost always kana-romanized Japanese (e.g. 스프레, 후쿠스루,
    스레바니, 사등픽뮤). Length-2 tokens are tolerated since open-syllable
    Korean nouns like 마리/꼬리/유리/어서 do exist."""
    for c in token:
        code = ord(c)
        if not (0xAC00 <= code <= 0xD7A3):
            continue
        if (code - 0xAC00) % 28 != 0:
            return False
    return True


def clean_record(text: str) -> str:
    text = VAR_RE.sub(" ", text)
    text = ANGLE_RE.sub(" ", text)
    text = NOISE_CHARS_RE.sub("", text)
    return text


def split_at_particles_and_endings(s: str) -> str:
    """Insert spaces around particles (after) and verb endings (before).
    The ROM corpus is mostly un-spaced; this is what recovers word tokens."""
    # Verb endings: insert space BEFORE
    for ending in ENDINGS:
        s = re.sub(rf"(?<=[가-힣])({re.escape(ending)})(?![가-힣])", r" \1", s)
    # Particles: insert space AFTER, only when followed by another Hangul
    for p in PARTICLES:
        s = re.sub(rf"({re.escape(p)})(?=[가-힣])", r"\1 ", s)
    return s


def strip_particle(token: str) -> str:
    for p in PARTICLES:
        if len(token) > len(p) and token.endswith(p):
            stripped = token[: -len(p)]
            if stripped and all(is_hangul(c) for c in stripped):
                return stripped
    return token


def deconjugate(token: str) -> str:
    if not token:
        return token

    # Hada first
    for suffix, replacement in HADA_FORMS:
        if token.endswith(suffix) and len(token) > len(suffix):
            return token[: -len(suffix)] + replacement

    # Standard endings
    for ending in ENDINGS:
        if token.endswith(ending) and len(token) > len(ending):
            stem = token[: -len(ending)]
            if stem and all(is_hangul(c) for c in stem):
                return stem + "다"

    return token  # noun (or unrecognized)


def romanize_syllable(c: str) -> str:
    INITIALS = ["g","kk","n","d","tt","r","m","b","pp","s","ss","","j","jj","ch","k","t","p","h"]
    VOWELS = ["a","ae","ya","yae","eo","e","yeo","ye","o","wa","wae","oe","yo","u","wo","we","wi","yu","eu","ui","i"]
    FINALS = ["","g","kk","gs","n","nj","nh","d","l","lg","lm","lb","ls","lt","lp","lh","m","b","bs","s","ss","ng","j","ch","k","t","p","h"]
    code = ord(c) - 0xAC00
    if code < 0 or code >= 11172:
        return c
    return INITIALS[code // 588] + VOWELS[(code % 588) // 28] + FINALS[code % 28]


def romanize(text: str) -> str:
    return "".join(romanize_syllable(c) if is_hangul(c) else c for c in text)


# ---------------------------------------------------------------------------
# Mining
# ---------------------------------------------------------------------------


def fluent_records(corpus: dict) -> tuple[list[dict], set[str]]:
    """Compute global Hangul char frequency, return records that pass a
    'fluent' test (mostly common characters)."""
    freq: Counter[str] = Counter()
    for r in corpus["records"]:
        for c in r.get("text", ""):
            if is_hangul(c):
                freq[c] += 1
    common = {c for c, _ in freq.most_common(500)}

    fluent: list[dict] = []
    for r in corpus["records"]:
        if r.get("unknown", 0) > 1:
            continue
        text = clean_record(r.get("text", ""))
        han = [c for c in text if is_hangul(c)]
        if len(han) < 4:
            continue
        common_ratio = sum(1 for c in han if c in common) / len(han)
        if common_ratio < 0.92:  # 92% top-500 chars
            continue
        # Also reject records with very low character diversity (repeated junk)
        if len(set(han)) / len(han) < 0.3:
            continue
        # Reject records dominated by Japanese-kana-rendered-as-Korean bigrams.
        # The live-region corpus contains untranslated leftovers where the
        # original Japanese kana was just transliterated into the closest-
        # sounding Korean syllables. These bigrams are common in those
        # passages and almost never appear in genuine Korean prose.
        kana_bigrams = ("누쿠", "무스", "케에", "하쿠", "케우", "노쿠", "등노",
                        "케이", "리쿠", "이쿠", "이뇨", "이본", "이딘", "닷노",
                        "키누", "키니", "키쿠", "키케", "딘이", "쿠쿤",
                        "스켄", "이파", "와쿠", "냐쿠")
        kana_hits = sum(text.count(b) for b in kana_bigrams)
        # Each hit is 2 chars; >12% of the record being kana bigrams = noise.
        if kana_hits * 2 > len(text) * 0.12:
            continue
        # Require at least one strong-confidence Korean grammar/dialog
        # marker. Records without any of these are almost always either
        # untranslated kana-romaji or pure menu fragments that don't
        # produce useful sentences.
        ko_markers = ("이에", "예요", "이야", "이지", "있어", "있다",
                      "한다", "해요", "하다", "어요", "어!", "어?",
                      "는걸", "은데", "을게", "지요", "다.", "다!",
                      "다?", "다。", "이다", "있는", "다는", "는데",
                      "받았", "주세", "고있", "고싶", "주마", "라구")
        if not any(m in text for m in ko_markers):
            continue
        fluent.append(r)
    return fluent, common


def mine(threshold: int, limit: int | None) -> tuple[list[dict], list[dict], dict]:
    corpus = json.loads(CORPUS.read_text())
    seed = json.loads(SEED.read_text())
    seed_terms = {e["korean"] for e in seed["entries"]}

    records, _common = fluent_records(corpus)
    stats = {"total_records": len(corpus["records"]), "fluent_records": len(records)}

    lemma_freq: Counter[str] = Counter()
    lemma_examples: dict[str, list[tuple]] = defaultdict(list)

    for r in records:
        text = clean_record(r["text"])
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
            # Reject sentences that look like Japanese romanization (don't end
            # in a plausible Korean verb/adjective ending, OR contain too many
            # kana-rendering bigrams).
            sentence_stripped = sentence.rstrip(" .!?,。…")
            ends_korean = KOREAN_END_RE.search(sentence_stripped) is not None
            has_particle = len(PARTICLE_PROBE_RE.findall(sentence)) >= 1
            # OR (not AND): item descriptions / Pokédex titles often have a
            # particle but no verb-ending; exclamations end with a verb but
            # have no particle. Either signal is enough evidence the line
            # is real Korean rather than kana-rendered Japanese.
            if not (ends_korean or has_particle):
                continue
            jp_hits = sum(1 for pat in JAPANESE_ROM_PATTERNS if pat in sentence)
            if jp_hits >= 1:
                continue
            # Tokenize. Prefer mecab-ko when installed — it gives proper
            # POS tags + lemmatization (강해져 → 강해지다). Falls back to
            # the regex-based heuristic below for environments without the
            # mecab-ko Python package.
            seen_in_sentence: set[str] = set()
            if _MECAB is not None:
                pairs = mecab_lemmatize(sentence)
            else:
                spaced = split_at_particles_and_endings(sentence)
                spaced = NON_HANGUL_RE.sub(" ", spaced)
                pairs = []
                for t in spaced.split():
                    t = strip_particle(t)
                    if not t:
                        continue
                    lem = deconjugate(t)
                    if lem:
                        pairs.append((lem, "verb/adj?" if lem.endswith("다") else "noun?", t))
            for lemma, lemma_pos, surface in pairs:
                if not lemma or len(lemma) < 2 or len(lemma) > 5:
                    continue
                # All-Hangul check: drop any token that picked up Latin/digits.
                if not all(is_hangul(c) for c in lemma):
                    continue
                # Reject tokens carrying Japanese-romanization signature.
                if any(pat in lemma for pat in JAPANESE_ROM_PATTERNS):
                    continue
                if is_phonetic_noise(lemma):
                    continue
                if len(lemma) >= 3 and not lemma.endswith("다") and has_no_batchim(lemma):
                    # Skip romanization-shaped nouns; spare verb/adj lemmas
                    # which always end in 다 and may be open-syllable stems.
                    continue
                if lemma_pos == "noun" and is_kana_shape_token(lemma):
                    continue
                if lemma in STOPWORDS or lemma in seed_terms:
                    continue
                if lemma in seen_in_sentence:
                    continue
                seen_in_sentence.add(lemma)
                lemma_freq[lemma] += 1
                lemma_examples[lemma].append((r["id"], surface, sentence, len(sentence), lemma_pos))

    candidates = [(l, n) for l, n in lemma_freq.items() if n >= threshold]
    candidates.sort(key=lambda kv: (-kv[1], kv[0]))
    if limit:
        candidates = candidates[:limit]
    stats["mined"] = len(candidates)

    vocab_entries: list[dict] = []
    sent_entries: list[dict] = []
    for lemma, freq in candidates:
        exs = lemma_examples[lemma]
        # Pick the shortest sentence with the surface form, prefer surface form
        # closest in length to the lemma (less inflection noise).
        exs.sort(key=lambda e: (e[3], abs(len(e[1]) - len(lemma))))
        rec_id, surface, sentence, _, lemma_pos = exs[0]
        pos = lemma_pos
        vocab_id = f"{SOURCE_TAG}:{lemma}"
        vocab_entries.append(
            {
                "korean": lemma,
                "romanization": romanize(lemma),
                "gloss": f"(unglossed; freq {freq})",
                "partOfSpeech": pos,
                "areaId": AREA_ID,
                "frequency": freq,
            }
        )
        sent_entries.append(
            {
                "vocabId": vocab_id,
                "korean": sentence,
                "romanization": romanize(sentence),
                "gloss": f"(ROM example, rec{rec_id})",
                "targetForm": surface,
                "areaId": AREA_ID,
                "source": f"rom-rec{rec_id}",
            }
        )

    return vocab_entries, sent_entries, stats


def main() -> int:
    global CORPUS, OUT_VOCAB, OUT_SENTS
    p = argparse.ArgumentParser()
    p.add_argument("--threshold", type=int, default=15)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--corpus", type=Path, default=None,
                   help="Override corpus path (default: app/src/main/assets/moneo/corpus.ko.json). "
                        "Use to mine the live-region corpus: --corpus tools/moneo/corpus.ko.live.json")
    p.add_argument("--out-vocab", type=Path, default=None,
                   help="Override seed-vocab output path.")
    p.add_argument("--out-sents", type=Path, default=None,
                   help="Override sentences output path.")
    args = p.parse_args()
    if args.corpus:
        CORPUS = args.corpus
    if args.out_vocab:
        OUT_VOCAB = args.out_vocab
    if args.out_sents:
        OUT_SENTS = args.out_sents

    vocab, sents, stats = mine(args.threshold, args.limit)
    print(f"Corpus: {CORPUS.relative_to(ROOT) if CORPUS.is_relative_to(ROOT) else CORPUS}")
    print(f"Records: {stats['total_records']} total, {stats['fluent_records']} fluent")
    print(f"Mined {stats['mined']} lemmas at threshold {args.threshold}")

    if args.dry_run:
        for v, s in zip(vocab[:60], sents[:60]):
            print(f"  {v['korean']:6s} ({v['frequency']:>3}x) [{v['partOfSpeech']:10s}]  surface={s['targetForm']:<6s}  ex: {s['korean'][:50]}")
        return 0

    OUT_VOCAB.write_text(json.dumps({
        "version": 1, "sourceTag": SOURCE_TAG,
        "notes": (f"Auto-mined from {CORPUS.name} at frequency threshold {args.threshold}. "
                  "Lemmatization is heuristic — irregular conjugations and polysemous "
                  "fragments may misclassify. Glosses are placeholders."),
        "entries": vocab,
    }, ensure_ascii=False, indent=2))
    OUT_SENTS.write_text(json.dumps({
        "version": 1, "sourceTag": SOURCE_TAG,
        "notes": "One ROM sentence per mined lemma; targetForm pins the surface form.",
        "entries": sents,
    }, ensure_ascii=False, indent=2))
    print(f"Wrote {OUT_VOCAB}")
    print(f"Wrote {OUT_SENTS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
