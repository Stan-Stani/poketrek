# Attribution coverage audit (2024-02-29 Korean ROM)

Final state after migrating from the 2010 fan-translation to the 2024-02-29
Korean patch (BPGE-canonical pokefirered rebuild).
Generated: 2026-05-07.

## Card-level attribution

```
TOPIK 1+2:       712 / 713  (99.86%)
ROM-mined:       165 / 165  (100%)
Combined:        877 / 878  (99.89%)
```

Live-mined deck (244 lemmas mined fresh from corpus.ko.live; not shipped):
226/244 attributed (93%); the 18 unattributed are 2-syllable Pokémon-name
fragments left over from kana-romaji noise the per-record decoder doesn't
cleanly reject (요프, 어보, 납기, 만코리, 소캐, 화구, 히브, 하터, 블디디, 요그,
파통, 후론, 후윤, 난고, 샤터, 진난, 쿠크, 페달). They are dropped from the
staged file. The shipped deck composition (TOPIK + ROM-mined) is unchanged.

The single unattributed TOPIK card is **시대 (era)** — the same noun that
fell out on the 2010 ROM. It genuinely does not appear in any in-game text
on either Korean build.

## Vs the 2010 ROM

| Metric | 2010 | 2024 | delta |
|--------|------|------|-------|
| Combined attribution % | 99.89% (950/951) | 99.89% (877/878) | tied |
| Maps walked | 146 | 299 | +153 |
| Live corpus records | 40,073 | 44,481 | +4,408 |
| Walker reach (records) | 4,800 | 4,426 | -374 |
| Maps with direct mapsec match | 108/146 | 276/299 | +168 |
| Maps unresolved by warps | 0 | 5 | +5 |
| Distinct areas in deck | 17 | 30 | +13 |

The 2024 patch's wider area distribution comes from:
- 153 more maps walked (the patch ships every canonical FRLG map, including
  Sevii Islands; the 2010 build had only Kanto)
- pokefirered-canonical mapsec assignments (the 2010 build had several
  shared "interior" mapsecs that pinned all interiors of one city to one
  mapsec; 2024 uses the canonical per-building values)

Walker reach is slightly lower because the 2024 patch's bytecode uses
more `loadword + callstd 0x6` indirection for trainer dialogs than direct
`message 0x67`, and some new pokefirered opcode paths aren't yet modeled
in walk_scripts_v2. This shows up as fewer records reached but does not
affect per-card attribution since the lemma index supplements via the
static trainer-table region (0x230000-0x240000) and the per-NPC trainer
class index.

## Walker reach summary (top 15 areas by recIds attributed)

| Area | recIds |
|------|--------|
| pallet_town | 1142 |
| celadon_city | 1127 |
| pewter_city | 1093 |
| route_4 | 855 |
| viridian_city | 846 |
| cinnabar_island | 845 |
| fuchsia_city | 840 |
| four_island (Sevii) | 828 |
| saffron_city | 794 |
| seven_island (Sevii) | 775 |
| vermilion_city | 738 |
| route_10 | 730 |
| cerulean_city | 705 |
| two_island (Sevii) | 696 |
| route_16 | 658 |

These counts are for ROM record IDs, not deck cards. A single record can
contain multiple lemmas, hence the much higher record counts than card counts.

## Combined deck distribution by firstAreaEncountered

| Area | Cards |
|------|-------|
| rom_mined | 463 |
| pallet_town | 184 |
| trainer_dialog | 62 |
| viridian_city | 48 |
| pewter_city | 25 |
| cerulean_city | 19 |
| route_4 | 11 |
| saffron_city | 9 |
| route_12 | 6 |
| fuchsia_city | 6 |
| (20 other areas) | ~14 |
| unattributed | 1 |

`rom_mined` (463 cards) is the static-corpus fallback for vocab that only
appears in Pokédex entries / item descriptions / menus rather than in
world-NPC dialog. These cards are still 100% attributed, just not to a
specific story-progression area.

## Re-running the audit

```bash
source .venv-moneo/bin/activate
python3 tools/moneo/fill_unattributed.py            # final pass: 877/878
```

The classifier was re-run against the 2024 ROM's live corpus and yielded
the same "no translated text missed" conclusion as the 2010 audit. The
38,000+ "isolated unreached" records on the 2024 ROM are kana-romaji
fragments the engine reads as opcode arguments or graphics-table indices,
never as player-facing text.

## Limitations

- 1 deck card (시대) and 18 dropped artifact lemmas: not in the game
- ~38K corpus records that are kana-romaji noise: never player-facing
- Sentence rotation finds in-area examples for ~54 cards on the 2024 ROM
  (vs 71 on 2010); the rest still use their static-corpus example sentence.
  This dipped because the live-corpus scan now extends to 0xED8000 and
  pulls more deeply-buried duplicates that don't beat the static example.
