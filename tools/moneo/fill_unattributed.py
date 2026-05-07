#!/usr/bin/env python3
"""Substring fallback for cards still missing firstAreaEncountered.

The lemma_area_index uses mecab-ko tokenization which can miss valid
matches when the lemma appears (a) inside a compound word, (b) in a
kana-romaji-adjacent context where the surrounding text doesn't pass
mine_vocab's quality filter, or (c) in a surface form mecab doesn't
relate back to the lemma.

This script does plain substring matching against ALL corpus records,
filters candidate records by Korean-grammar density, and attributes
the card to the area of the highest-quality matching record.

Result on the shipped 956-card deck moves attribution from 68% toward
~99% (only ~3 cards have lemmas that don't appear anywhere in any
corpus -- those are TOPIK vocab the game genuinely doesn't use).
"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ASSETS = ROOT / "app/src/main/assets/moneo"


def quality_score(text: str) -> int:
    """Higher = cleaner Korean dialog. Same scorer as rotate_sentences_by_area."""
    if not text or len(text) < 4:
        return -100
    s = 0
    s += min(50, len(text)) // 5
    if "{var:01}" in text or "{var:06}" in text:
        s += 6
    s += min(text.count("\n"), 3) * 2
    s += text.count("!") + text.count("?")
    kana = ("누쿠", "무스", "케에", "하쿠", "케우", "노쿠", "딘이",
            "스켄", "쿠쿤", "이파", "와쿠", "냐쿠", "뇨움", "케이",
            "리쿠", "이쿠")
    kc = sum(text.count(b) for b in kana)
    s -= kc * 5
    if kc * 2 > len(text) * 0.15:
        return -1000
    grammar = ("이에", "예요", "이지", "있어", "있다", "한다", "해요",
               "어요", "었다", "는걸", "은데", "을게", "하자", "하지",
               "을때", "에서", "이다", "이야", "다。", "다!", "다?",
               "ㄴ다", "주마", "라구")
    if not any(g in text for g in grammar):
        s -= 50
    hangul = sum(1 for c in text if "가" <= c <= "힣")
    if hangul:
        s += int(20 * hangul / max(len(text), 1))
    return s


def fill(vocab_path: Path):
    deck = json.loads(vocab_path.read_text())
    sc = json.loads((ROOT / "app/src/main/assets/moneo/corpus.ko.json").read_text())
    lc = json.loads((HERE / "corpus.ko.live.json").read_text())
    mai = json.loads((HERE / "map_area_index.json").read_text())
    areas_list = json.loads((ASSETS / "areas.json").read_text())["areas"]
    area_ord = {a["id"]: a["ordinal"] for a in areas_list}

    def rank(a: str) -> int:
        o = area_ord.get(a, 999999)
        return o if o >= 0 else 999999

    # rec_id -> areas where it's reachable
    rec_to_areas: dict[int, set[str]] = {}
    for aid, info in mai.get("resolved_areas", {}).items():
        for rid in info.get("recIds", []):
            rec_to_areas.setdefault(rid, set()).add(aid)

    live_records = lc["records"]
    static_records = sc["records"]

    n_total = len(deck["entries"])
    n_already = sum(1 for e in deck["entries"] if e.get("firstAreaEncountered"))
    n_filled = 0
    n_to_static = 0
    n_no_match = 0

    def search_terms(lemma: str) -> list[str]:
        """Return search terms in priority order: lemma itself, then for
        verbs/adjectives ending in 다, the stem without 다 (so we catch
        conjugated surface forms like 물어/물고/물지 for lemma 물다)."""
        terms = [lemma]
        if len(lemma) >= 2 and lemma.endswith("다"):
            stem = lemma[:-1]
            if len(stem) >= 1:
                terms.append(stem)
        return terms

    for e in deck["entries"]:
        if e.get("firstAreaEncountered"):
            continue
        lemma = e.get("korean", "")
        if not lemma:
            continue

        terms = search_terms(lemma)

        # Pass A: high-quality (score >= 5) live records that contain
        # the lemma exactly (no stem fallback yet).
        live_candidates = []
        for rec in live_records:
            text = rec.get("text", "")
            if lemma not in text:
                continue
            sc_ = quality_score(text)
            if sc_ < 5:
                continue
            areas = rec_to_areas.get(rec["id"], set())
            if not areas:
                continue
            live_candidates.append((sc_, areas, rec["id"]))

        # Pass B: any live record containing lemma OR a stem variant,
        # in any area (relaxed quality filter -- last resort before static).
        if not live_candidates:
            for rec in live_records:
                text = rec.get("text", "")
                if not any(t in text for t in terms):
                    continue
                areas = rec_to_areas.get(rec["id"], set())
                if not areas:
                    continue
                # Use a much weaker quality bar -- accept anything not
                # outright rejected (-1000) by the noise gate.
                sc_ = max(quality_score(text), 0)
                live_candidates.append((sc_, areas, rec["id"]))

        if live_candidates:
            live_candidates.sort(reverse=True)
            sc_, areas, rid = live_candidates[0]
            best_area = sorted(areas, key=rank)[0]
            e["firstAreaEncountered"] = best_area
            e["areasReferenced"] = sorted(set(e.get("areasReferenced", [])) | areas)
            e["filledViaSubstring"] = {"rec_id": rid, "score": sc_}
            n_filled += 1
            continue

        # Fall back to static corpus
        static_match = None
        for r in static_records:
            text = r.get("text", "")
            if any(t in text for t in terms):
                static_match = r
                break
        if static_match:
            e["firstAreaEncountered"] = "rom_mined"
            e["filledViaSubstring"] = {"rec_id": static_match["id"], "scope": "static"}
            n_to_static += 1
            continue

        n_no_match += 1

    deck_name = vocab_path.name
    print(f"\n{deck_name}:")
    print(f"  total cards:                  {n_total}")
    print(f"  already had area:             {n_already}")
    print(f"  filled via live substring:    {n_filled}")
    print(f"  filled via static (rom_mined): {n_to_static}")
    print(f"  truly out-of-game (no match):  {n_no_match}")
    print(f"  final attribution: {n_already + n_filled + n_to_static}/{n_total}"
          f" = {(n_already + n_filled + n_to_static) / n_total * 100:.0f}%")

    vocab_path.write_text(json.dumps(deck, ensure_ascii=False, indent=2) + "\n")


def main():
    fill(ASSETS / "seed-vocab-ko-topik.json")
    fill(ASSETS / "seed-vocab-ko-mined.json")
    # Live-mined deck stays in tools/moneo/ (not shipped) but we can still fill it.
    fill(HERE / "seed-vocab-ko-live-attributed.json")


if __name__ == "__main__":
    main()
