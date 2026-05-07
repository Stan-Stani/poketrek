# ROM swap workflow

Swap the broken 2010 Korean fan-translation for the 2024-02-29 patch
(99.6% complete). Bundled tools: patch downloader, applier, ROM-offset
diagnostic.

## What's here

```
rom_swap/
├── README.md                       # this file
├── apply_patch.py                  # applies leafgreen_J-K.xdelta to a Japanese ROM
└── diagnose.py                     # checks whether existing tools/moneo offsets work on a ROM
```

The .xdelta patch files and any .gba ROM are gitignored. Fetch the
patches first (one-time):

```bash
mkdir -p tools/moneo/rom_swap
curl -L -o /tmp/2024patch.zip \
    "https://drive.google.com/uc?export=download&id=1PtJ7YplZBdN8Yvb3cw-w9hrt-sT2trPt"
python3 -c "
import zipfile
with zipfile.ZipFile('/tmp/2024patch.zip') as z:
    for info in z.infolist():
        # filenames are UTF-8 bytes mis-decoded as cp437 by Python's zipfile
        raw = info.filename.encode('cp437')
        kr = raw.decode('utf-8', errors='replace')
        if '리프그린' in kr: out = 'tools/moneo/rom_swap/leafgreen_J-K.xdelta'
        elif '파이어레드' in kr: out = 'tools/moneo/rom_swap/firered_J-K.xdelta'
        elif '에메랄드' in kr: out = 'tools/moneo/rom_swap/emerald_J-K.xdelta'
        elif '가이드' in kr: out = 'tools/moneo/rom_swap/README_korean.txt'
        else: continue
        with open(out, 'wb') as f: f.write(z.read(info))
        print(f'  {out}')
"
```

Patch authors: 명군 (lead), tony, koi, 돌아온달토끼.

## What you need to do

1. **Acquire a Japanese FRLG ROM** (1.0). The patch readme specifies:
   - **LeafGreen Japan 1.0**: MD5 = `138a71a5be83f3f3d7af3d31916a5fc7`
   - (FireRed Japan 1.0: `47596db5a16556c60027e7bf372ec917`)
   - (Emerald Japan 1.0:  `92eecf93f1ab828bdf2a83daddacf3e5`)

   Place it somewhere accessible, e.g. `~/roms/leafgreen_japan.gba`.

2. **Apply the patch:**

   ```bash
   source .venv-moneo/bin/activate
   python3 tools/moneo/rom_swap/apply_patch.py ~/roms/leafgreen_japan.gba
   # writes -> tools/moneo/rom_swap/leafgreen_J-K_2024.gba
   ```

   If the MD5 doesn't match, the script warns but still tries; xdelta3 will
   fail with `XD3_INVALID_INPUT` if the base is too different.

3. **Diagnose which offsets need re-derivation:**

   ```bash
   python3 tools/moneo/rom_swap/diagnose.py tools/moneo/rom_swap/leafgreen_J-K_2024.gba
   ```

   Reports per-offset PASS/FAIL for the 7 hardcoded tables (gMapGroups,
   gItems, gPokedexEntries, gWildMonHeaders, gTrainers, gTrainerClassNames,
   trainer-dialog region). With `--quick`, skips the (slower) signature
   re-search step.

   Expected outcome for a 2024-patched ROM:
   - **gMapGroups**: probably moves (the 2024 patch may relocate maps)
   - **Item / Pokedex / WildMon tables**: likely stable, since these are
     engine data structures the translators didn't relocate.
   - **gTrainers**: probably 40-byte canonical pokefirered stride, NOT the
     32-byte Korean compacted stride (the 2024 patch is more thorough,
     less likely to have shrunk struct sizes for space).
   - **gTrainerClassNames**: stride may differ; the Korean fan-build had
     11-byte entries.

4. **Re-derive any failed offsets** using the signature-search snippets in:
   - `git show 3b2ddb0` — items_table.json + item_obtain_index.json
   - `git show 5619b0f` — pokedex_table.json + pokedex_obtain_index.json
   - `git show a6c1fd5` — trainer_class_names.json
   - `git show 0fe15b9` — trainer_npc_index.json + gTrainers location

5. **Add a new ROM variant in `app/src/main/kotlin/com/poketrek/emu/RomIdentity.kt`**:

   ```kotlin
   val LEAFGREEN_KR_2024 = RomVariant(
       crc32 = 0x________,    // CRC32 of patched ROM (from diagnose.py output)
       label = "LeafGreen Korean 2024-02-29",
       gatingSupported = true,
   )
   ```

   The 2010 Korean ROM remains supported via its existing entry; Phase 0
   tests will verify both ROMs render deterministically.

6. **Re-run the moneo pipeline** with the new ROM (see `RUNBOOK.md`):

   ```bash
   # Update tools/moneo/probe_map_text.py's ROM constant + GROUP_OFFSETS if changed
   python3 tools/moneo/extend_corpus_live.py
   python3 tools/moneo/walk_scripts_v2.py
   python3 tools/moneo/resolve_map_areas.py
   python3 tools/moneo/build_live_lemma_index.py
   python3 tools/moneo/attribute_existing_decks.py
   python3 tools/moneo/fill_unattributed.py
   python3 tools/moneo/rotate_sentences_by_area.py
   ```

## What you'll likely gain

| Metric | 2010 patch (now) | 2024 patch (projected) |
|--------|-----------------|------------------------|
| Translation completeness | ~mid-game stops | ~99.6% |
| Live records reached + translated | ~4,800 / 40K (12%) | ~25K+ / 40K (60%+) |
| Move/ability descriptions | kana noise | translated |
| Trainer dialog (minor trainers) | kana noise | translated |
| Sevii Islands extras | kana noise | translated |
| Sentence rotation hits per card | 71/950 | likely 500+/950 |
| Trainer names | translated (mostly) | translated + Korean canonical names |
| Untranslated remaining | 33K records | Trainer Tower + some graphics + asm |

Patch authors: **명군** (lead) + tony, koi, 돌아온달토끼.
Discussion threads: dcinside `mgallery/board/view/?id=game_nintendo&no=2515975`,
hangulogame.com post 844.

## Safety notes

- We did NOT commit the .gba ROMs (gitignored). The .xdelta patch files
  ARE committed since they're publicly distributed.
- The patch is a third-party fan work; the existing 2010 ROM stays in
  place until you've validated the new one boots and renders correctly
  in the emulator.
- Re-derivation costs: probably 1-3 hours of signature scripts running
  + one session of glyph-map verification, NOT a full RE redo.
