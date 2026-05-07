#!/usr/bin/env python3
"""Merge the move/ability deck into the shipped seed-vocab-ko-mined.json
and matching sentences. Also copy the species deck into the assets dir.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
ASSETS = ROOT / "app/src/main/assets/moneo"


def merge_vocab(existing_path: Path, additions_path: Path, out_path: Path):
    existing = json.loads(existing_path.read_text())
    additions = json.loads(additions_path.read_text())
    by_korean: dict[str, dict] = {}
    for e in existing["entries"]:
        by_korean[e["korean"]] = e
    added = 0
    for e in additions["entries"]:
        if e["korean"] not in by_korean:
            by_korean[e["korean"]] = e
            added += 1
    # Preserve existing notes; append a new note line.
    existing_notes = list(existing.get("notes", []))
    existing_notes.append(
        f"Merged {added} new cards from gMoveNames + gAbilityNames in "
        f"the 2024 patched ROM ({len(additions['entries'])} candidates "
        f"after dedup against existing {len(existing['entries'])} entries)."
    )
    out = {
        "version": existing.get("version", 1),
        "sourceTag": existing["sourceTag"],
        "notes": existing_notes,
        "entries": list(by_korean.values()),
    }
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"  vocab: {len(existing['entries'])} -> {len(out['entries'])} (+{added})")


def merge_sentences(existing_path: Path, additions_path: Path, out_path: Path,
                    valid_vocab_ids: set[str]):
    existing = json.loads(existing_path.read_text())
    additions = json.loads(additions_path.read_text())
    # Dedupe by (vocabId, korean) like the test expects
    seen = {(e["vocabId"], e["korean"]) for e in existing["entries"]}
    new_entries = list(existing["entries"])
    added = 0
    for e in additions["entries"]:
        key = (e["vocabId"], e["korean"])
        if key in seen:
            continue
        if e["vocabId"] not in valid_vocab_ids:
            # Skip orphan sentences
            continue
        seen.add(key)
        new_entries.append(e)
        added += 1
    notes = list(existing.get("notes", []))
    notes.append(f"Merged {added} new ROM-name sentences.")
    out = {
        "version": existing.get("version", 1),
        "sourceTag": existing.get("sourceTag", "rom-mine-v2"),
        "notes": notes,
        "entries": new_entries,
    }
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"  sentences: {len(existing['entries'])} -> {len(new_entries)} (+{added})")


def main():
    # Merge move/ability cards into the shipped mined deck
    mined_in = ASSETS / "seed-vocab-ko-mined.json"
    rom_names_in = HERE / "seed-vocab-ko-rom-names.json"
    merge_vocab(mined_in, rom_names_in, mined_in)

    # Re-read updated vocab to compute valid vocab IDs for sentence merge
    updated = json.loads(mined_in.read_text())
    source_tag = updated["sourceTag"]
    valid_ids = {f"{source_tag}:{e['korean']}" for e in updated["entries"]}

    # Merge sentences
    sents_mined_in = ASSETS / "sentences-ko-mined.json"
    sents_rom_names_in = HERE / "sentences-ko-rom-names.json"
    merge_sentences(sents_mined_in, sents_rom_names_in, sents_mined_in, valid_ids)

    # Copy species deck (separate file; not auto-loaded)
    species_in = HERE / "seed-vocab-ko-species.json"
    species_out = ASSETS / "seed-vocab-ko-species.json"
    species_out.write_text(species_in.read_text())
    print(f"  species deck: copied to {species_out.relative_to(ROOT)}")

    sents_species_in = HERE / "sentences-ko-species.json"
    sents_species_out = ASSETS / "sentences-ko-species.json"
    sents_species_out.write_text(sents_species_in.read_text())
    print(f"  species sentences: copied to {sents_species_out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
