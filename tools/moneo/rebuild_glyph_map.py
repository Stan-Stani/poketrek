#!/usr/bin/env python3
"""Build the correct ROM (page, idx_byte) -> Korean char translation table.

Formula derived from render_dialogue_v8.py's font addressing:
  file_offset = FONT_BASE + rom_page * 0x2000 + idx_byte * 32
               = FONT_BASE + (rom_page // 2) * 0x4000
                 + (rom_page % 2) * 0x2000 + idx_byte * 32

Which maps to glyph_table key:
  gt_fp  = rom_page // 2 + 1
  gt_gid = (rom_page % 2) * 256 + idx_byte
  key    = f"F{gt_fp},{gt_gid}"

Coverage:
  ROM 0xF1 (page=1) -> F1, gid=256..511
  ROM 0xF2 (page=2) -> F2, gid=0..255
  ROM 0xF3 (page=3) -> F2, gid=256..511
  ROM 0xF4 (page=4) -> F3, gid=0..255
  ROM 0xF5 (page=5) -> F3, gid=256..511
  ROM 0xF6 (page=6) -> F4, gid=0..255
"""
import json
from pathlib import Path

GT_PATH = ".moneo-artifacts/glyph-table.json"
KS_PATH = ".moneo-artifacts/ksx1001-charmap.json"
KO_PATH = "app/src/main/assets/moneo/ko_charmap.json"
GM_PATH = "tools/moneo/glyph-map.json"

def rom_to_gt_key(rom_page, idx_byte):
    """ROM (page 1-6, idx 0-255) -> glyph_table key string."""
    gt_fp = rom_page // 2 + 1
    gt_gid = (rom_page % 2) * 256 + idx_byte
    return f"F{gt_fp},{gt_gid}"

def main():
    gt = json.loads(Path(GT_PATH).read_text())
    ks = json.loads(Path(KS_PATH).read_text())
    ko = json.loads(Path(KO_PATH).read_text())

    print("=== Verifying formula with known chars ===")
    # 하 should be at glyph_table F1,434
    # ROM (page=1, idx=178): gt_fp=1, gt_gid=256+178=434 -> F1,434
    print(f"ROM(p=1, idx=178) -> {rom_to_gt_key(1,178)} -> {gt.get('F1,434','?')!r} (expected 하)")
    
    # Check overlap with ko_charmap chars
    ko_chars = set(ko.values())
    print(f"\nko_charmap chars ({len(ko_chars)} unique): {sorted(ko_chars)[:10]}...")

    # Build full map for all (page, idx) pairs in ROM corpus
    raw = json.loads(Path(".moneo-artifacts/rom-text-ko-raw.json").read_text())
    
    # Collect distinct tokens
    tokens = {}
    for rec in raw['records']:
        h = rec['hex']
        bs = bytes.fromhex(h)
        i = 0
        while i < len(bs):
            b = bs[i]
            if b == 0xFF: break
            if 0xF1 <= b <= 0xF6 and i+1 < len(bs):
                p = b - 0xF0
                idx = bs[i+1]
                tokens[(p, idx)] = tokens.get((p, idx), 0) + 1
                i += 2
            elif b in (0xFC, 0xFD) and i+1 < len(bs):
                i += 2
            else:
                i += 1

    print(f"\nDistinct ROM tokens: {len(tokens)}")

    # Build glyph-map in F{page},{idx} format (for build_corpus.py)
    # Key format: "F{rom_page},{idx_byte}" -> Korean char
    new_map = {}
    resolved = 0
    unresolved = []
    
    for (rom_page, idx_byte), cnt in sorted(tokens.items()):
        gt_key = rom_to_gt_key(rom_page, idx_byte)
        ch = gt.get(gt_key)
        rom_key = f"F{rom_page},{idx_byte}"
        if ch:
            new_map[rom_key] = ch
            resolved += 1
        else:
            unresolved.append((rom_page, idx_byte, gt_key, cnt))

    print(f"Resolved: {resolved}/{len(tokens)}")
    print(f"Unresolved: {len(unresolved)} (no glyph_table entry)")
    if unresolved[:5]:
        print("Sample unresolved:", unresolved[:5])

    # How many ko_charmap chars are in new_map?
    ko_found = {ch: [] for ch in ko_chars}
    for key, ch in new_map.items():
        if ch in ko_found:
            ko_found[ch].append(key)
    
    ko_covered = sum(1 for v in ko_found.values() if v)
    print(f"\nko_charmap chars covered by new_map: {ko_covered}/{len(ko_chars)}")
    print("ko_charmap chars and their ROM positions:")
    for ch in sorted(ko_chars):
        positions = ko_found.get(ch, [])
        print(f"  {ch!r}: {positions[:3]}")

    # Also try ksx1001-charmap as a fallback for unresolved tokens
    # ksx1001-charmap key format: F{vram_page},{linear_pos}
    # The vram positions might correspond to glyph_table gids via a different formula
    # For now, try: if gt_key missing, try ks directly
    fallback = 0
    for rom_page, idx_byte, gt_key, cnt in unresolved:
        # Try ksx1001 at same position
        ch = ks.get(gt_key)
        if ch:
            new_map[f"F{rom_page},{idx_byte}"] = ch
            fallback += 1
    print(f"\nFallback from ksx1001-charmap: {fallback} additional entries")

    # Save glyph-map.json in format expected by build_corpus.py
    # build_corpus.py reads: glyph_data["map"] where keys are "F{page},{idx}"
    existing = json.loads(Path(GM_PATH).read_text())
    existing_map = existing.get("map", {})
    existing_conf = existing.get("confidence", {})
    
    # Merge: new_map takes priority over existing (OCR-based)
    merged_map = dict(existing_map)
    merged_map.update(new_map)
    
    print(f"\nExisting glyph-map entries: {len(existing_map)}")
    print(f"New entries: {len(new_map)}")
    print(f"Merged total: {len(merged_map)}")
    
    # Write updated glyph-map.json
    updated = {"map": merged_map, "confidence": existing_conf}
    Path(GM_PATH).write_text(json.dumps(updated, ensure_ascii=False, indent=1))
    print(f"Wrote {GM_PATH} with {len(merged_map)} entries")

if __name__ == "__main__":
    main()
