#!/usr/bin/env python3
"""Extract Korean root vocabulary from species-name etymology notes.

Each species card in seed-vocab-ko-species.json has a `notes` field like:
  "메 (mountain) + 꿀꿀 (oink) — mountain pig"
  "잉어 (carp) + 킹 (king, English)"
  "이상해 (strange) + 씨 (seed)"

This script parses those into individual Korean root vocab cards. Dedupes
across species; for each root tracks: gloss, source species, first area.

Output: app/src/main/assets/moneo/seed-vocab-ko-etymology.json
        app/src/main/assets/moneo/sentences-ko-etymology.json (one example sentence per root, generated from species names containing it)

The deck is opt-in via prefs.includeEtymology. sourceTag is "etymology-roots"
so the runtime filter can include/exclude as a unit.
"""
from __future__ import annotations
import json, re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
SPECIES_PATH = ROOT / "app/src/main/assets/moneo/seed-vocab-ko-species.json"
AREAS_PATH = ROOT / "app/src/main/assets/moneo/areas.json"
TOPIK_PATH = ROOT / "app/src/main/assets/moneo/seed-vocab-ko-topik.json"
MINED_PATH = ROOT / "app/src/main/assets/moneo/seed-vocab-ko-mined.json"
LEGACY_PATH = ROOT / "app/src/main/assets/moneo/seed-vocab-ko.json"
OUT_VOCAB = ROOT / "app/src/main/assets/moneo/seed-vocab-ko-etymology.json"
OUT_SENTS = ROOT / "app/src/main/assets/moneo/sentences-ko-etymology.json"


# Match patterns like "메 (mountain)" — one Korean run + parenthesized gloss
COMPONENT_RE = re.compile(r"([가-힣]+)\s*\(([^)]+)\)")


# Skip these "roots" — they're suffixes, particles, or nondescriptive markers
EXCLUDED_ROOTS = {
    # Generic suffixes the agent labeled as such
    "라", "키", "모", "이", "다",
    # Short articles / particles that snuck in
    "은", "는", "을", "를", "이", "가",
    # Single-syllable bound morphemes that aren't real standalone vocab
    "조",  # bird (Sino-Korean) — already in compounds, keep? actually keep it.
}
# Override: re-include "조" since it's a useful Sino-Korean morpheme
EXCLUDED_ROOTS.discard("조")


# Skip glosses that mark something as not-a-real-root
EXCLUDED_GLOSS_PATTERNS = (
    "suffix", "Pokémon name", "variant", "evolution", "Pokemon", "abbrev",
)


def romanize(korean: str) -> str:
    """Quick Revised Romanization. Not perfect, but consistent."""
    initial = {
        "ㄱ":"g", "ㄲ":"kk", "ㄴ":"n", "ㄷ":"d", "ㄸ":"tt", "ㄹ":"r",
        "ㅁ":"m", "ㅂ":"b", "ㅃ":"pp", "ㅅ":"s", "ㅆ":"ss", "ㅇ":"",
        "ㅈ":"j", "ㅉ":"jj", "ㅊ":"ch", "ㅋ":"k", "ㅌ":"t", "ㅍ":"p", "ㅎ":"h",
    }
    medial = {
        "ㅏ":"a", "ㅐ":"ae", "ㅑ":"ya", "ㅒ":"yae", "ㅓ":"eo", "ㅔ":"e",
        "ㅕ":"yeo", "ㅖ":"ye", "ㅗ":"o", "ㅘ":"wa", "ㅙ":"wae", "ㅚ":"oe",
        "ㅛ":"yo", "ㅜ":"u", "ㅝ":"wo", "ㅞ":"we", "ㅟ":"wi", "ㅠ":"yu",
        "ㅡ":"eu", "ㅢ":"ui", "ㅣ":"i",
    }
    final = {
        "":"", "ㄱ":"k", "ㄲ":"k", "ㄳ":"k", "ㄴ":"n", "ㄵ":"n", "ㄶ":"n",
        "ㄷ":"t", "ㄹ":"l", "ㄺ":"k", "ㄻ":"m", "ㄼ":"l", "ㄽ":"l", "ㄾ":"l",
        "ㄿ":"p", "ㅀ":"l", "ㅁ":"m", "ㅂ":"p", "ㅄ":"p", "ㅅ":"t", "ㅆ":"t",
        "ㅇ":"ng", "ㅈ":"t", "ㅊ":"t", "ㅋ":"k", "ㅌ":"t", "ㅍ":"p", "ㅎ":"h",
    }
    INIT = list("ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ")
    MED = list("ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ")
    FIN = ["", "ㄱ", "ㄲ", "ㄳ", "ㄴ", "ㄵ", "ㄶ", "ㄷ", "ㄹ", "ㄺ", "ㄻ",
           "ㄼ", "ㄽ", "ㄾ", "ㄿ", "ㅀ", "ㅁ", "ㅂ", "ㅄ", "ㅅ", "ㅆ", "ㅇ",
           "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"]
    out = []
    for c in korean:
        n = ord(c) - 0xAC00
        if 0 <= n < 11172:
            i, m, f = n // 588, (n // 28) % 21, n % 28
            out.append(initial[INIT[i]] + medial[MED[m]] + final[FIN[f]])
        else:
            out.append(c)
    return "".join(out)


def main():
    species = json.loads(SPECIES_PATH.read_text())
    areas = {a["id"]: a["ordinal"] for a in json.loads(AREAS_PATH.read_text())["areas"]}

    # Already-known Korean lemmas across other decks — skip these
    existing = set()
    for path in (TOPIK_PATH, MINED_PATH, LEGACY_PATH):
        if path.exists():
            d = json.loads(path.read_text())
            existing |= {e["korean"] for e in d["entries"]}

    # Walk species notes; harvest (root, gloss) per species
    # root -> {"gloss": str, "species": [(korean_name, english_gloss, area)], ...}
    roots = defaultdict(lambda: {"glosses": [], "species": []})

    for entry in species["entries"]:
        notes = entry.get("notes", "")
        if not notes:
            continue
        # Skip pure-loanword entries — no Korean roots to teach
        if notes.lower().startswith(("loanword", "japanese loanword", "transliteration")):
            continue
        # Strip the trailing clarifier after em-dash
        head = notes.split("—", 1)[0]
        for m in COMPONENT_RE.finditer(head):
            root = m.group(1).strip()
            gloss = m.group(2).strip()
            if not root or root in EXCLUDED_ROOTS:
                continue
            if any(p in gloss.lower() for p in EXCLUDED_GLOSS_PATTERNS):
                continue
            if root in existing:
                continue
            roots[root]["glosses"].append(gloss)
            roots[root]["species"].append({
                "korean": entry["korean"],
                "english": entry.get("gloss", "").replace(" (Pokemon)", ""),
                "area": entry.get("firstAreaEncountered", "rom_mined"),
            })

    print(f"Found {len(roots)} unique etymology roots (after filtering)")

    # Build deck entries
    def rank_area(a):
        o = areas.get(a, 999999)
        return o if o >= 0 else 999998

    vocab_entries = []
    sent_entries = []
    for root, info in sorted(roots.items()):
        # Pick most-common gloss
        from collections import Counter
        gloss_top = Counter(info["glosses"]).most_common(1)[0][0]
        # First-encountered area = lowest-ordinal among species using this root
        sp_areas = [(rank_area(s["area"]), s["area"]) for s in info["species"]]
        sp_areas.sort()
        first_area = sp_areas[0][1] if sp_areas else "rom_mined"
        all_areas = sorted({s["area"] for s in info["species"]})

        # Build a "from X (Y), Z (W)..." note showing leverage
        leverage = ", ".join(
            f"{s['korean']} ({s['english']})" for s in info["species"][:4]
        )
        if len(info["species"]) > 4:
            leverage += f" + {len(info['species']) - 4} more"

        notes = f"From {leverage}"

        vocab_entries.append({
            "id": f"etymology-roots:{root}",
            "korean": root,
            "romanization": romanize(root),
            "gloss": gloss_top,
            "partOfSpeech": "root/morpheme",
            "areaId": first_area,
            "sourceTag": "etymology-roots",
            "notes": notes,
            "frequency": len(info["species"]),
            "firstAreaEncountered": first_area,
            "areasReferenced": all_areas,
            "componentOf": [s["korean"] for s in info["species"]],
        })

        # Generate one example sentence: a species name containing the root
        # e.g. for 곰 (bear), example is 링곰 (Ursaring): "링곰" with translation
        ex_sp = info["species"][0]
        sent_entries.append({
            "vocabId": f"etymology-roots:{root}",
            "korean": ex_sp["korean"],
            "romanization": romanize(ex_sp["korean"]),
            "gloss": f"{ex_sp['english']} — contains the root '{root}'",
            "targetForm": root,
            "areaId": first_area,
            "source": "etymology",
        })

    out_vocab = {
        "version": 1,
        "sourceTag": "etymology-roots",
        "notes": (
            "Korean root morphemes harvested from species-name pun etymologies. "
            "Each card teaches a Korean root that appears as a component of one or "
            "more Pokemon names. Opt-in via Settings > Etymology root cards."
        ),
        "entries": vocab_entries,
    }
    out_sents = {
        "version": 1,
        "notes": "Example: a species name containing the root.",
        "entries": sent_entries,
    }
    OUT_VOCAB.write_text(json.dumps(out_vocab, ensure_ascii=False, indent=2) + "\n")
    OUT_SENTS.write_text(json.dumps(out_sents, ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote {OUT_VOCAB.name}: {len(vocab_entries)} root cards")
    print(f"Wrote {OUT_SENTS.name}: {len(sent_entries)} example sentences")

    # Show top 20 most-leveraged roots
    print(f"\nTop 20 most-leveraged roots (appears in N species):")
    top = sorted(vocab_entries, key=lambda e: -e["frequency"])[:20]
    for e in top:
        print(f"  {e['korean']:<6} ({e['gloss']:<30}) appears in {e['frequency']:>2} species")


if __name__ == "__main__":
    main()
