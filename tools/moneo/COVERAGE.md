# Attribution coverage audit

Final state after all 7 lemma-index passes + substring fallback.
Generated: 2026-05-07.

## Card-level attribution

```
TOPIK 1+2:       712 / 713  (99.86%)
ROM-mined:       165 / 165  (100%)
Live-mined:       73 /  73  (100% after dropping 5 kana-romaji artifact lemmas)
Combined:        950 / 951  (99.89%)
```

The single unattributed card is **시대 (era)** — a TOPIK noun that genuinely
does not appear in any text in this Pokémon ROM. The 5 dropped live-mined
entries (무차/노르/미란/미혼/삼본) were tokenization artifacts mecab extracted
from kana-romaji noise; they aren't real Korean words.

## Text-record-level attribution

### Static corpus (`corpus.ko.json`)
- **8,488 records, all attributed** to `rom_mined` (with item/Pokédex/trainer
  passes promoting many to specific areas via the lemma index).
- 418 of those are clean translated text (Pokédex entries, item descriptions,
  menus). The rest are the leftover `힌힌{VDD}` records that survived from the
  original Japanese region.

### Live corpus (`corpus.ko.live.json`) — 40,073 records
| Status | Count | Notes |
|--------|-------|-------|
| Reached + canonical area | **4,800** | The walker found a script-bytecode path |
| Within 64 bytes of a reached record | 1,585 | Sliding-window duplicates of the same text |
| Within 500 bytes of a reached record | 253 | Same script context, different start offset |
| Isolated (>500 bytes from any reached) | 33,435 | Untranslated kana-romaji noise — see below |

### Why 33K records are "isolated unreached"

Sample records 9999, 10000, 10001 at offsets `0x100`, `0x101`, `0x102`:

```
rec9999  @ 0x100: '오   아   프롯딘닷론롯날미윈톤닷닷날미...'
rec10000 @ 0x101: '   아   프롯딘닷론롯날미윈톤닷닷날미...'
rec10001 @ 0x102: '  아   프롯딘닷론롯날미윈톤닷닷날미...'
```

Three identical sentences shifted by one byte each. The corpus extractor
(`extend_corpus_live.py`) accepts every u32-pointer-target as a record start
and emits each separately. Most of these starts land inside Japanese romaji
(Pokémon names, Trainer ID strings) that the fan-translation never converted.
The player never sees "롯딘닷론롯날미윈톤" as readable text in-game — it's
encoded data the engine reads as opcode arguments or graphics-table indices.

After re-classifying 35,273 unreached records by quality:

| Record class | Count |
|-------------|-------|
| Strict-translated (multi-grammar, low kana density) | **0** with isolated-from-reached |
| Sliding-window duplicate of a reached record | 1,585 |
| Kana-romaji noise (Japanese phonetic data) | 33,435 |

**Conclusion: every translated text record in the ROM is attributed**, either
directly via the script walker (4,800 in canonical areas) or indirectly via
overlap with a walker-reached record (+1,585 within 64 bytes). The remaining
33,435 are extractor artifacts the player never reads.

## Walker reach summary

By area (top 15, from `map_area_index.json`):

| Area | recIds attributed |
|------|-------------------|
| pallet_town | 938 |
| fuchsia_city | 847 |
| four_island | 802 (Sevii) |
| viridian_city | 796 |
| cinnabar_island | 762 |
| seven_island | 704 (Sevii) |
| cerulean_city | 700 |
| two_island | 686 (Sevii) |
| celadon_city | varies |
| route_4 | 358 |

These counts are for ROM record IDs, not deck cards. A single record can
contain multiple lemmas, hence the much higher record counts than card counts.

## Limitations

- 1 deck card (시대) and 5 dropped artifact lemmas: not in the game
- ~33K corpus records that are kana-romaji noise: never player-facing
- Sentence rotation only finds in-area examples for ~71 cards; the rest still
  use their static-corpus example sentence

## Re-running the audit

```bash
source .venv-moneo/bin/activate
python3 tools/moneo/fill_unattributed.py            # final pass: 950/951
```

Diagnostic snippets used for this audit are in commit messages
`a7f7e07` (substring fallback) and follow-on commits. The classifier in this
report uses a strict-translated heuristic that requires both grammar markers
AND low kana-romaji bigram density.
