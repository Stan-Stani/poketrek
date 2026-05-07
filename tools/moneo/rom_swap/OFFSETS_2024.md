# ROM offsets for the 2024-02-29 Korean LeafGreen patch (BPGE-canonical)

ROM: `tools/moneo/rom_swap/leafgreen_J-K_2024.gba`
- MD5: `4c9e97dab5c8d80c1448dfcace442a2d`
- CRC32: `0x4A38A8CB`
- Game code: BPGE (canonical FRLG/LG layout, pokefirered struct sizes)
- Size: 16,777,216 bytes

| Symbol | New offset (2024) | Old offset (2010) | Stride | Count | Notes |
|--------|-------------------|-------------------|--------|-------|-------|
| gMapGroups | 0x352700 | 0x316740 | 4 | 41 | Group ptrs; same Korean ordering as 2010 |
| gItems | 0x3DAED4 | 0x3A058C | **44** | 375 | Canonical FRLG Item struct (was 40-byte Korean compacted) |
| gPokedexEntries | 0x44E2E0 | 0x40E254 | **36** | 387 | Canonical PokedexEntry (was 28-byte Korean compacted) |
| gWildMonHeaders | 0x3C9B64 | 0x390E04 | 20 | 132+ | Group offset still `-2` (canonical mg → ROM mg) |
| gTrainers | 0x23EB3C | 0x1FE1B4 | **40** | 743 | Canonical FRLG Trainer struct (was 32-byte Korean compacted) |
| gTrainerClassNames | 0x23E5A4 | 0x1FDB18 | **13** | 107 | Canonical FRLG (was 11-byte Korean compacted) |

## Struct strides

The 2024 patch uses **canonical pokefirered struct sizes** for all major tables.
The 2010 fan-build had compacted them. Specifically:

| Struct | Canonical | 2010 | 2024 |
|--------|-----------|------|------|
| Item | 44 | 40 | 44 |
| PokedexEntry | 36 | 28 | 36 |
| Trainer | 40 | 32 | 40 |
| TrainerClassName | 13 | 11 | 13 |

## gMapGroups indexing

The 2024 ROM has 41 groups in this order (same as Korean 2010 fan-build):

| ROM group | Maps | Canonical pokefirered | mapsec[0] |
|-----------|------|------------------------|-----------|
| 0 | 60 | gMapGroup_SpecialArea | 0xAE |
| 1 | 66 | gMapGroup_TownsAndRoutes | 0x58 (Pallet) |
| 2 | 4 | gMapGroup_IndoorPallet | 0x58 |
| 3 | 6 | gMapGroup_IndoorViridian | 0x59 |
| 4 | 8 | gMapGroup_IndoorPewter | 0x5A |
| 5 | 10 | gMapGroup_IndoorCerulean | 0x5B |
| 6 | 6 | gMapGroup_IndoorLavender | 0x5C |
| 7 | 8 | gMapGroup_IndoorVermilion | 0x5D |
| 8 | 20 | gMapGroup_IndoorCeladon | 0x5E |
| 9 | 10 | gMapGroup_IndoorFuchsia | 0x5F |
| 10 | 8 | gMapGroup_IndoorCinnabar | 0x60 |
| ... | | | |

The Korean fan-build (both 2010 and 2024) drops the canonical `gMapGroup_Link`
and `gMapGroup_Dungeons` super-groups, so:

```
korean_walker_group = pokefirered_canonical_group - 2
```

This is the same `-2` offset the 2010 ROM needed. **The 2024 patch has NOT
removed this quirk** despite using canonical struct layouts.

`gWildMonHeaders` uses canonical pokefirered indexing for `mapGroup`, so when
walking the table you still need to apply `-2` to map to ROM group indices.

## Trainer dialog region

In the 2010 ROM this was 0x163000-0x166000. The 2024 ROM moves it (relocated
along with everything else). High-density text-pointer windows in the new ROM:
- 0x237000-0x238FFF (highest text-ptr density)
- 0x25D000
- 0x3AD000

The trainer-dialog scan should be re-bounded. Defer until after the walker
runs and we see if all trainer text gets reached via the script walker;
the standalone trainer-dialog region may not be needed.
