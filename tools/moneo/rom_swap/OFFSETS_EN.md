# English LeafGreen ROM offsets

ROM: `Pokemon - LeafGreen Version (USA, Europe) (Rev 1).gba`
CRC32: `0xDAFFECEC`
Gamecode: `BPGE`
Size: 16 MiB

## Name tables

All offsets derived by `find_offsets_en.py` (searches the ROM for known
anchor strings encoded in the Gen 3 English charset). Strides come from
pokefirered's `include/constants/pokemon.h` and `include/constants/moves.h`.

| Table                  | Offset      | Stride | Entries | Anchor [1]    |
|------------------------|------------:|-------:|--------:|---------------|
| `gSpeciesNames`        | `0x245F2C`  | 11     | 412     | `BULBASAUR`   |
| `gMoveNames`           | `0x2470E0`  | 13     | 355     | `POUND`       |
| `gAbilityNames`        | `0x24FC8C`  | 13     | 78      | `STENCH`      |
| `gItems` (name @ +0)   | `0x3DAED4`  | 44     | 375     | `MASTER BALL` |
| `gPokedexEntries` (cat @ +0) | `0x44E2E0` | 36 | 387     | `SEED`        |
| `gTrainerClassNames`   | `0x23E5A4`  | 13     | 107     | (encoded)     |

Entry `[0]` of every table is the placeholder/dummy slot (`?????????`,
`UNKNOWN`, etc.) — start the meaningful range at `[1]`.

## Why the offsets match the Korean 2024 patch

`tools/moneo/rom_config.py` carries the same offsets for the Korean 2024
patch. The match is incidental: the patch was rebuilt over the canonical
FRLG English layout rather than re-laying-out the binary. If a future EN
revision (or a different KR patch) ever drifts, `find_offsets_en.py`
catches it on the first run.

## Character encoding

`rom_config_en.EN_CHARMAP` covers printable ASCII (`A`-`Z`, `a`-`z`,
`0`-`9`, common punctuation, `♂`/`♀`). The terminator is `0xFF`. Inline
control prefixes `0xFC`/`0xFD`/`0xFE` introduce buffer/var/format codes
(`{PLAYER}`, `{RIVAL}`, `{COLOR x}`, …) — the scanner emits placeholders
for these rather than treating them as junk.
