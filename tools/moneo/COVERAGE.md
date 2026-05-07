# Attribution coverage audit (2026-05-07 Korean ROM)

Final state after merging move/ability/species cards from `gMoveNames`,
`gAbilityNames`, and `gSpeciesNames` in the 2024 patch (BPGE-canonical
pokefirered rebuild). Shipping commit: 237b39e.
Generated: 2026-05-07.

## Card-level attribution

```
seed-vocab-ko:        45 /  45  (100%)
TOPIK 1+2:           712 / 713  (99.86%)
ROM-mined:           619 / 619  (100%)
Species:             363 / 363  (100%)
Combined:           1739 /1740  (99.94%)
```

The single unattributed card remains **시대 (era)** — the same noun that
fell out on both the 2010 and 2024 ROMs. It genuinely does not appear in
any in-game text on either Korean build.

## Shipped deck composition

| Deck | Cards | Attribution | Source |
|------|-------|-------------|--------|
| seed-vocab-ko | 45 | 100% | Legacy base seed; uses areaId not firstAreaEncountered |
| seed-vocab-ko-mined | 619 | 100% | gMoveNames + gAbilityNames + ROM corpus; +424 from 2024 baseline |
| seed-vocab-ko-topik | 713 | 99.86% | TOPIK 1+2 curated lemma list (unchanged) |
| seed-vocab-ko-species | 363 | 100% | gSpeciesNames (new deck) |
| **Total** | **1740** | **99.94%** | |

## Name-table extraction summary

Three static name tables were decoded from the 2024 ROM using a custom
16-bit BE codepoint font (533 codepoints triangulated from PokeAPI
canonical Korean names + iterative resolution). This is **not** the
`F0..F6` page-byte scheme used by dialog text; it is a separate hangul
font table.

| Table | ROM offset | Stride | Entries | Cleanly decoded |
|-------|-----------|--------|---------|-----------------|
| gMoveNames | 0x2470E0 | 13 bytes | 355 | 349 |
| gAbilityNames | 0x24FC8C | 13 bytes | 78 | 77 |
| gSpeciesNames | 0x245F2C | 11 bytes | 412 | 363 |

The 363/412 species decode rate reflects ~25 placeholder entries
(`AC FF AC AC...`) representing untranslated Hoenn slots in the 2024
patch, plus ~24 Gen 3 species whose name encodings could not be fully
resolved against the font table.

## TM/HM-based move attribution

52 of the 349 decoded move names are attributed to specific game areas
via canonical FRLG TM/HM acquisition tables (TM01–TM50, HM01–HM08).

| Move | TM/HM | Area |
|------|-------|------|
| 화염방사 (Flamethrower) | TM35 | celadon_city |
| 지진 (Earthquake) | TM26 | viridian_city |
| 냉동빔 (Ice Beam) | TM13 | celadon_city |
| 10만볼트 (Thunderbolt) | TM24 | vermilion_city |
| 사이코키네시스 (Psychic) | TM29 | saffron_city |
| 파도타기 (Surf) | HM03 | safari_zone |
| (and 46 more) | | |

The remaining 297 move names are attributed from the ROM-mined static
corpus and carry no specific area assignment.

## Species first-area attribution

| Method | Species |
|--------|---------|
| Wild-encounter index | 64 |
| Hard-coded overrides | 6 |
| ROM-mined static corpus | 293 |
| **Total attributed** | **363** |

Hard-coded overrides apply to species that are never encountered in
tall grass or water:

| Species | Area |
|---------|------|
| Bulbasaur / Ivysaur / Venusaur | pallet_town |
| Charmander / Charmeleon / Charizard | pallet_town |
| Squirtle / Wartortle / Blastoise | pallet_town |
| Articuno | seafoam_islands |
| Zapdos | power_plant |
| Moltres | route_23 |
| Mewtwo | cerulean_cave |
| Snorlax | route_12 |
| Lapras | silph_co |

## Combined deck distribution by firstAreaEncountered

| Area | Cards |
|------|-------|
| rom_mined (static corpus) | 847 |
| pallet_town | 190 |
| trainer_dialog | 62 |
| viridian_city | 51 |
| pewter_city | 27 |
| cerulean_city | 21 |
| celadon_city | 15 |
| saffron_city | 11 |
| vermilion_city | 10 |
| fuchsia_city | 8 |
| route_12 | 6 |
| route_4 | 11 |
| wild_encounter | 64 |
| (28 other areas) | ~26 |
| unattributed | 1 |

`rom_mined` (847 cards) is the static-corpus fallback for vocab that only
appears in Pokédex entries, item descriptions, menus, and now move/ability
names that lack a TM/HM-area source. These cards are still 100% attributed,
just not to a specific story-progression area.

## Vs the prior audit (2024-02-29)

| Metric | Prior (2024-02-29) | Current (2026-05-07) | delta |
|--------|---------------------|----------------------|-------|
| Combined attribution % | 99.89% (877/878) | 99.94% (1739/1740) | +0.05% |
| Total cards shipped | 908 | 1740 | +832 |
| Decks in rotation | 3 | 4 | +1 (species) |
| TOPIK cards | 713 | 713 | 0 |
| ROM-mined cards | 165 | 619 | +454 |
| Species cards | 0 | 363 | +363 |
| Distinct areas in deck | 30 | 35 | +5 |
| Area-attributed mined cards | 159 | 211 | +52 |
| Unattributed | 1 | 1 | 0 |

The massive increase in card count comes from three name-table extractions
that were previously out of scope:
- **gMoveNames**: 349 move name cards (+52 TM/HM-attributed to areas)
- **gAbilityNames**: 77 ability name cards
- **gSpeciesNames**: 363 species name cards (+70 to areas via encounters)

The 2024-02-29 ROM-mined deck (165 cards) was folded into the expanded
mined deck alongside the name-table extractions; legacy cards were
deduplicated against the new gMoveNames/gAbilityNames extraction.

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

Walker reach and area-level record distribution are unchanged from the
2024-02-29 audit; the new cards are sourced from static tables, not
live-corpus walker traversal.

## Re-running the audit

```bash
source .venv-moneo/bin/activate
python3 tools/moneo/fill_unattributed.py            # final pass: 1739/1740
```

The classifier was re-run against the expanded deck and confirmed the
"시대" outlier remains the sole unattributed card. The species deck was
validated by cross-referencing gSpeciesNames output against PokeAPI
canonical Korean names; all 363 shipped entries resolve correctly.

## Limitations

- 1 deck card (시대) unattributed: not present in any game text
- 25 species placeholders (`AC FF AC AC...`): untranslated Hoenn slots
  in the 2024 patch; excluded from the shipped species deck
- ~17 codepoints still ambiguous in the font table (digits, ♀/♂, HP);
  affected name-table entries are shipped with partial-decoded glosses
  rather than dropped
- 297 move names and 293 species names have no TM/HM or encounter-area
  attribution; they carry `rom_mined` as their firstAreaEncountered
- The live-corpus walker was not re-run for this audit; all new cards
  derive from the static name tables and existing corpus indices