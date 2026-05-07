#!/usr/bin/env python3
"""Build per-area item / pokedex / trainer-class indexes for the 2024 Korean ROM.

Walks every map's scripts (reusing walk_scripts_v2 framework) to detect:
  - additem (0x44) / pokemart (0x86, 0x87, 0x88) -> per-area itemIds
  - trainerbattle (0x5C) -> per-area trainerIds (then trainer class via gTrainers)
And separately walks gWildMonHeaders for per-area species (first-encounter).

Outputs:
  tools/moneo/item_obtain_index.json
  tools/moneo/pokedex_obtain_index.json
  tools/moneo/trainer_npc_index.json
"""
from __future__ import annotations
import json
import struct
import sys
from collections import defaultdict
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))

from rom_config import (  # noqa: E402
    ROM_PATH, GBA_BASE,
    GMAP_GROUPS,
    GITEMS, GITEMS_STRIDE, GITEMS_DESC_OFF, GITEMS_ITEMID_OFF,
    GTRAINERS, GTRAINERS_STRIDE, GTRAINERS_CLASS_OFF,
    GWILD_MON_HEADERS, GWILD_STRIDE,
    KOREAN_GROUP_OFFSET,
    get_group_offsets, u32, u16, is_rom_ptr,
)
from script_opcodes import (  # noqa: E402
    OPCODES,
    LOADWORD_OPCODE,
    CALLSTD_OPCODE,
    CALL_GOTO_OPCODES,
    CALL_GOTO_IF_OPCODES,
    END_OPCODES,
    BUFFERSTRING_OPCODES,
    TRAINERBATTLE_LAYOUTS,
)
from walk_scripts_v2 import walk_maps, collect_seed_scripts  # noqa: E402

ROOT = THIS_DIR.parents[1]
MAPSEC_AREAS_PATH = THIS_DIR / "mapsec_areas.json"
AREAS_PATH = ROOT / "app/src/main/assets/moneo/areas.json"
ITEMS_TABLE_PATH = THIS_DIR / "items_table.json"
POKEDEX_TABLE_PATH = THIS_DIR / "pokedex_table.json"
TRAINER_CLASS_NAMES_PATH = THIS_DIR / "trainer_class_names.json"

ITEM_OUT = THIS_DIR / "item_obtain_index.json"
POKEDEX_OUT = THIS_DIR / "pokedex_obtain_index.json"
TRAINER_OUT = THIS_DIR / "trainer_npc_index.json"


# Opcodes we care about for per-map indexing
ADDITEM_OPCODE = 0x44
REMOVEITEM_OPCODE = 0x45
POKEMART_OPCODES = {0x86, 0x87, 0x88}
TRAINERBATTLE_OPCODE = 0x5C


def walk_script_collect(rom: bytes, seed: int, depth: int = 2):
    """Walk a single seed script via the same opcode-table mechanics as
    walk_scripts_v2. Yields tuples per detected event:
        ('additem', itemId), ('pokemart', [itemId, ...]),
        ('trainerbattle', trainerId).
    """
    rom_len = len(rom)
    visited: set[int] = set()
    queue: list[tuple[int, int]] = [(seed, depth)]

    while queue:
        off, dep = queue.pop()
        if off in visited or off >= rom_len or off < 0:
            continue
        visited.add(off)
        cur = off
        while cur < rom_len:
            op = rom[cur]

            if op == ADDITEM_OPCODE:
                if cur + 5 > rom_len: break
                item_id = u16(rom, cur + 1)
                yield ('additem', item_id)
                cur += 5
                continue

            if op in POKEMART_OPCODES:
                if cur + 5 > rom_len: break
                p = u32(rom, cur + 1)
                if is_rom_ptr(p, rom_len):
                    base = p - GBA_BASE
                    items = []
                    for k in range(80):
                        if base + k * 2 + 2 > rom_len: break
                        v = u16(rom, base + k * 2)
                        if v == 0:
                            break
                        items.append(v)
                    if items:
                        yield ('pokemart', items)
                cur += 5
                continue

            if op == TRAINERBATTLE_OPCODE:
                if cur + 4 > rom_len: break
                subtype = rom[cur + 1]
                trainer_id = u16(rom, cur + 2)
                yield ('trainerbattle', trainer_id)
                layout = TRAINERBATTLE_LAYOUTS.get(subtype)
                if layout is None:
                    cur += 8
                else:
                    cur += layout[0]
                continue

            if op in END_OPCODES:
                break

            if op in CALL_GOTO_OPCODES:
                if cur + 5 > rom_len: break
                p = u32(rom, cur + 1)
                if is_rom_ptr(p, rom_len) and dep > 0:
                    queue.append((p - GBA_BASE, dep - 1))
                # call returns; goto does not. Treat call as continue, goto as break.
                if op == 0x04:  # call
                    cur += 5
                    continue
                else:  # 0x05 = goto
                    break

            if op in CALL_GOTO_IF_OPCODES:
                if cur + 6 > rom_len: break
                p = u32(rom, cur + 2)
                if is_rom_ptr(p, rom_len) and dep > 0:
                    queue.append((p - GBA_BASE, dep - 1))
                cur += 6
                continue

            if op in BUFFERSTRING_OPCODES:
                # 0x85 / 0xBF: opcode + stringVarId(1) + ptr u32 = 6 bytes
                cur += 6
                continue

            spec = OPCODES.get(op)
            if spec is None:
                cur += 1
                continue
            length = spec.get("length")
            if length is None:
                # variable-length opcodes we don't model; advance 1
                cur += 1
                continue
            cur += length


def load_mapsec_to_area():
    data = json.loads(MAPSEC_AREAS_PATH.read_text())
    out: dict[int, str] = {}
    for k, v in data.get("mapsecs", {}).items():
        try:
            ms = int(k, 0)
        except ValueError:
            continue
        if v.get("area_id"):
            out[ms] = v["area_id"]
    return out


def load_area_ordinals():
    data = json.loads(AREAS_PATH.read_text())
    # areas.json is { areas: [{id, ordinal, ...}] } based on existing pipeline use
    if isinstance(data, dict) and "areas" in data:
        areas = data["areas"]
    else:
        areas = data
    out: dict[str, int] = {}
    for a in areas:
        aid = a.get("id")
        ord_v = a.get("ordinal")
        if aid and ord_v is not None:
            out[aid] = ord_v
    return out


def load_items_table():
    d = json.loads(ITEMS_TABLE_PATH.read_text())
    # itemId -> rec_id
    out: dict[int, int] = {}
    for it in d["items"]:
        rid = it.get("description_rec_id")
        iid = it.get("item_id")
        if iid is not None and rid is not None:
            out[iid] = rid
    return out


def load_pokedex_table():
    d = json.loads(POKEDEX_TABLE_PATH.read_text())
    out: dict[int, int] = {}
    for e in d["entries"]:
        sid = e.get("species_index")
        rid = e.get("description_rec_id")
        if sid is not None and rid is not None:
            out[sid] = rid
    return out


def load_trainer_class_names():
    d = json.loads(TRAINER_CLASS_NAMES_PATH.read_text())
    return {c["class_id"]: c["text"] for c in d["classes"]}


def main():
    rom = ROM_PATH.read_bytes()
    rom_len = len(rom)
    mapsec_to_area = load_mapsec_to_area()
    area_ord = load_area_ordinals()
    item_recids = load_items_table()
    dex_recids = load_pokedex_table()
    class_names = load_trainer_class_names()

    # Walk all maps
    area_items: dict[str, set[int]] = defaultdict(set)  # area -> {itemId}
    area_trainers: dict[str, set[int]] = defaultdict(set)
    n_pokemarts = 0
    n_giveitems = 0
    maps_with_trainers = 0
    total_trainer_hits = 0

    for g, i, mh, mapsec, music in walk_maps(rom):
        area = mapsec_to_area.get(mapsec)
        seeds = collect_seed_scripts(rom, mh)
        any_trainer = False
        for seed in seeds:
            if not is_rom_ptr(seed + GBA_BASE, rom_len):
                continue
            for evt in walk_script_collect(rom, seed):
                kind = evt[0]
                if kind == 'additem':
                    n_giveitems += 1
                    if area:
                        area_items[area].add(evt[1])
                elif kind == 'pokemart':
                    n_pokemarts += 1
                    if area:
                        for iid in evt[1]:
                            area_items[area].add(iid)
                elif kind == 'trainerbattle':
                    total_trainer_hits += 1
                    any_trainer = True
                    if area:
                        area_trainers[area].add(evt[1])
        if any_trainer:
            maps_with_trainers += 1

    # Build item_obtain_index
    area_item_recids: dict[str, list[int]] = {}
    for area, items in area_items.items():
        recs = sorted({item_recids[iid] for iid in items if iid in item_recids})
        if recs:
            area_item_recids[area] = recs
    item_out = {
        "version": 2,
        "rom": "leafgreen_J-K_2024.gba",
        "pokemarts": n_pokemarts,
        "giveitems": n_giveitems,
        "area_to_item_rec_ids": dict(sorted(area_item_recids.items())),
    }
    ITEM_OUT.write_text(json.dumps(item_out, ensure_ascii=False, indent=1) + "\n")
    print(f"item_obtain_index.json: {len(area_item_recids)} areas, "
          f"{n_pokemarts} pokemarts, {n_giveitems} giveitems")

    # Build trainer_npc_index
    n_trainers_with_class = 0
    area_class_names: dict[str, list[str]] = {}
    for area, tids in area_trainers.items():
        names: set[str] = set()
        for tid in tids:
            if tid >= 743:
                continue
            cls_id = rom[GTRAINERS + tid * GTRAINERS_STRIDE + GTRAINERS_CLASS_OFF]
            name = class_names.get(cls_id, "")
            if name:
                names.add(name)
                n_trainers_with_class += 1
        if names:
            area_class_names[area] = sorted(names)
    trainer_out = {
        "version": 2,
        "rom": "leafgreen_J-K_2024.gba",
        "gtrainers_offset": GTRAINERS,
        "gtrainers_stride": GTRAINERS_STRIDE,
        "trainers_in_maps": maps_with_trainers,
        "trainers_with_class": n_trainers_with_class,
        "area_to_trainer_class_names": dict(sorted(area_class_names.items())),
    }
    TRAINER_OUT.write_text(json.dumps(trainer_out, ensure_ascii=False, indent=1) + "\n")
    print(f"trainer_npc_index.json: {len(area_class_names)} areas, "
          f"{maps_with_trainers} maps with trainers, "
          f"{total_trainer_hits} trainerbattle hits")

    # === Pokedex obtain index from gWildMonHeaders ===
    group_offsets = get_group_offsets(rom)
    n_groups_rom = len(group_offsets) - 1

    # Build (canonical_mg, mn) -> mapsec lookup using ROM gMapGroups (Korean ordering)
    mapsec_by_korean_group_mn: dict[tuple[int, int], int] = {}
    for korean_g in range(n_groups_rom):
        start, end = group_offsets[korean_g], group_offsets[korean_g + 1]
        n_maps = (end - start) // 4
        for mn in range(n_maps):
            p = u32(rom, start + mn * 4)
            if not is_rom_ptr(p, rom_len):
                continue
            mh = p - GBA_BASE
            if mh + 21 > rom_len:
                continue
            mapsec = rom[mh + 20]
            mapsec_by_korean_group_mn[(korean_g, mn)] = mapsec

    # species -> (best_area_ordinal, area_id)
    species_first_area: dict[int, tuple[int, str]] = {}

    SLOT_LAYOUTS = [
        ("land", 12),
        ("water", 5),
        ("rock", 5),
        ("fish", 10),
    ]

    n_wild = 0
    for i in range(200):
        e = GWILD_MON_HEADERS + i * GWILD_STRIDE
        if e + GWILD_STRIDE > rom_len:
            break
        canonical_mg = rom[e]
        mn = rom[e + 1]
        if canonical_mg == 0xFF and mn == 0xFF:
            break
        pad = u16(rom, e + 2)
        if pad != 0:
            break
        ptrs = [u32(rom, e + 4 + j * 4) for j in range(4)]
        if not all(p == 0 or is_rom_ptr(p, rom_len) for p in ptrs):
            break
        if not any(p != 0 and is_rom_ptr(p, rom_len) for p in ptrs):
            break
        n_wild += 1

        # canonical -> korean walker group
        korean_g = canonical_mg + KOREAN_GROUP_OFFSET
        if korean_g < 0:
            continue
        mapsec = mapsec_by_korean_group_mn.get((korean_g, mn))
        if mapsec is None:
            continue
        area = mapsec_to_area.get(mapsec)
        if area is None:
            continue
        ord_v = area_ord.get(area, 99)

        for j, (kind, n_slots) in enumerate(SLOT_LAYOUTS):
            wmi_ptr = ptrs[j]
            if wmi_ptr == 0:
                continue
            wmi = wmi_ptr - GBA_BASE
            if wmi + 8 > rom_len:
                continue
            # WildPokemonInfo: u8 encounterRate, u24 padding, ptr to WildPokemon[]
            wp_ptr = u32(rom, wmi + 4)
            if not is_rom_ptr(wp_ptr, rom_len):
                continue
            wp = wp_ptr - GBA_BASE
            for k in range(n_slots):
                wpe = wp + k * 4
                if wpe + 4 > rom_len:
                    break
                # WildPokemon: u8 minLevel, u8 maxLevel, u16 species
                species = u16(rom, wpe + 2)
                if species == 0 or species > 411:
                    continue
                cur = species_first_area.get(species)
                if cur is None or ord_v < cur[0]:
                    species_first_area[species] = (ord_v, area)

    # Build area_to_pokedex_rec_ids
    area_dex_recids: dict[str, list[int]] = defaultdict(list)
    for species, (_, area) in species_first_area.items():
        rid = dex_recids.get(species)
        if rid is None:
            continue
        area_dex_recids[area].append(rid)
    for a in area_dex_recids:
        area_dex_recids[a] = sorted(set(area_dex_recids[a]))

    pokedex_out = {
        "version": 2,
        "rom": "leafgreen_J-K_2024.gba",
        "wildmon_table_offset": GWILD_MON_HEADERS,
        "wildmon_stride": GWILD_STRIDE,
        "group_translation": f"pokefirered_group + {KOREAN_GROUP_OFFSET}",
        "method": "first-encounter-by-lowest-area-ordinal",
        "n_wild_headers": n_wild,
        "n_species_with_area": len(species_first_area),
        "area_to_pokedex_rec_ids": dict(sorted(area_dex_recids.items())),
    }
    POKEDEX_OUT.write_text(json.dumps(pokedex_out, ensure_ascii=False, indent=1) + "\n")
    print(f"pokedex_obtain_index.json: {len(area_dex_recids)} areas, "
          f"{n_wild} wild headers, {len(species_first_area)} species")


if __name__ == "__main__":
    main()
