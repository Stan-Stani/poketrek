#!/usr/bin/env python3
"""For each card with firstAreaEncountered, replace the example sentence
with one drawn from a live-corpus record IN that area (when available).

Otherwise keep the existing example. Updates seed-vocab*-attributed.json
and sentences*-attributed.json in-place.

Why: cards say "first encountered in <area>" but their example sentences
were picked at mining time from the STATIC corpus (Pokédex / items / menu)
because that's where the lemma's frequency was high. The example then
doesn't read like dialog from that area. Rotating to an in-area record's
text makes the deck feel coherent: card claim + example match.
"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LIVE = HERE / "corpus.ko.live.json"
STATIC = ROOT / "app/src/main/assets/moneo/corpus.ko.json"
MAP_AREA = HERE / "map_area_index.json"
ASSETS = ROOT / "app/src/main/assets/moneo"


def quality_score(text: str) -> int:
    """Higher = more usable as an example sentence.
    Prefer:
      - moderate length (15-80 chars)
      - high hangul ratio
      - presence of dialog markers (player-name var, line breaks, ! ?)
      - absence of kana-romaji bigrams
    """
    if not text:
        return -100
    if len(text) < 5:
        return -50
    if len(text) > 200:
        return -20
    s = 0
    s += min(50, len(text)) // 5  # length bonus up to ~10
    if "{var:01}" in text or "{var:06}" in text:
        s += 6
    s += min(text.count("\n"), 3) * 2
    s += text.count("!") + text.count("?")
    # penalize kana-romaji density HEAVILY -- a record dominated by these
    # bigrams is untranslated noise that we shouldn't surface as an example.
    kana_bigrams = ("누쿠", "무스", "케에", "하쿠", "케우", "노쿠", "딘이",
                    "스켄", "쿠쿤", "이파", "와쿠", "냐쿠", "뇨움", "케이",
                    "리쿠")
    kana_count = sum(text.count(b) for b in kana_bigrams)
    s -= kana_count * 5
    # Outright reject records where kana bigrams cover >15% of length
    if kana_count * 2 > len(text) * 0.15:
        return -1000
    # Require at least one Korean grammar marker -- otherwise it's
    # probably untranslated mid-sentence fragment
    grammar_markers = ("이에", "예요", "이지", "있어", "있다", "한다",
                       "해요", "어요", "었다", "는걸", "은데", "을게",
                       "하자", "하지", "을때", "에서", "이다", "이야",
                       "다。", "다!", "다?", "ㄴ다", "주마", "라구")
    if not any(m in text for m in grammar_markers):
        s -= 50
    # hangul ratio
    hangul = sum(1 for c in text if "가" <= c <= "힣")
    if hangul:
        s += int(20 * hangul / max(len(text), 1))
    return s


def best_example_in_area(lemma: str, area: str,
                         area_to_recs: dict, live_records: dict) -> dict | None:
    """Find the best live-corpus record containing `lemma` and reachable from `area`."""
    rec_ids = area_to_recs.get(area, set())
    candidates = []
    for rid in rec_ids:
        rec = live_records.get(rid)
        if not rec:
            continue
        text = rec.get("text", "")
        if lemma not in text:
            continue
        candidates.append((quality_score(text), rid, text))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    score, rid, text = candidates[0]
    # Refuse to rotate if the best candidate is still poor quality
    # (kana-romaji noise records lose this filter).
    if score < 5:
        return None
    return {"rec_id": rid, "text": text, "score": score}


def rotate_deck(vocab_name: str, sent_name: str, dry_run: bool):
    vocab_path = ASSETS / vocab_name
    sent_path = ASSETS / sent_name
    vocab = json.loads(vocab_path.read_text())
    sents = json.loads(sent_path.read_text())

    # rec_id -> live record
    live = json.loads(LIVE.read_text())
    live_records = {r["id"]: r for r in live["records"]}

    # area_id -> set of rec_ids reachable from there
    mai = json.loads(MAP_AREA.read_text())
    area_to_recs = {aid: set(info.get("recIds", []))
                    for aid, info in mai.get("resolved_areas", {}).items()}

    # Build vocab korean -> firstAreaEncountered
    vocab_first = {e["korean"]: e.get("firstAreaEncountered")
                   for e in vocab["entries"]}

    # For each sentence, try to rotate
    n_total = 0
    n_rotated = 0
    n_no_area = 0
    n_no_match = 0

    for sent in sents["entries"]:
        n_total += 1
        vid = sent.get("vocabId", "")
        # Extract lemma from vocabId 'sourceTag:lemma' or fall back to targetForm
        lemma = None
        if ":" in vid:
            lemma = vid.split(":", 1)[1]
        elif sent.get("targetForm"):
            lemma = sent["targetForm"]
        if not lemma:
            continue
        area = vocab_first.get(lemma)
        if not area:
            n_no_area += 1
            continue

        replacement = best_example_in_area(lemma, area, area_to_recs, live_records)
        if replacement is None:
            n_no_match += 1
            continue

        # Replace sentence text + record original (keep original if rotating again)
        if "originalKorean" not in sent:
            sent["originalKorean"] = sent.get("korean")
            sent["originalSource"] = sent.get("source")
        sent["korean"] = replacement["text"]
        sent["source"] = f"rom-rec{replacement['rec_id']}"
        sent["rotatedFromArea"] = area
        n_rotated += 1

    print(f"\n{vocab_name}:")
    print(f"  total sentences:           {n_total}")
    print(f"  rotated to in-area record: {n_rotated}")
    print(f"  card has no area:          {n_no_area}")
    print(f"  no in-area record contains lemma: {n_no_match}")

    if not dry_run:
        sent_path.write_text(json.dumps(sents, ensure_ascii=False, indent=2) + "\n")
        print(f"  wrote {sent_path}")


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="Report counts but don't write files.")
    args = ap.parse_args()
    rotate_deck("seed-vocab-ko-topik.json", "sentences-ko-topik.json", args.dry_run)
    rotate_deck("seed-vocab-ko-mined.json", "sentences-ko-mined.json", args.dry_run)


if __name__ == "__main__":
    main()
