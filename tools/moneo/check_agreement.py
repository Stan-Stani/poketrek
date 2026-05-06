#!/usr/bin/env python3
"""Check agreement between glyph_table and ksx1001-charmap at shared positions."""
import json

gt = json.load(open('.moneo-artifacts/glyph-table.json'))
ks = json.load(open('.moneo-artifacts/ksx1001-charmap.json'))

# Check overlap
shared = set(gt.keys()) & set(ks.keys())
print(f"Shared keys: {len(shared)}")

agree = sum(1 for k in shared if gt[k] == ks[k])
print(f"Agreement: {agree}/{len(shared)} = {100*agree/len(shared):.1f}%")

# Sample disagreements
disagree = [(k, gt[k], ks[k]) for k in sorted(shared) if gt[k] != ks[k]]
print(f"\nFirst 20 disagreements (key, gt, ks):")
for k, g, s in disagree[:20]:
    print(f"  {k}: gt={g!r} ks={s!r}")

print("\nFirst 20 agreements:")
agr_list = [(k, gt[k]) for k in sorted(shared) if gt[k] == ks[k]]
for k, c in agr_list[:20]:
    print(f"  {k}: {c!r}")

# Check how many distinct gt values are 미, 디 etc. (OCR garbage)
garbage_chars = ['미','디','의','의','이','이']
garbage = {k:v for k,v in gt.items() if v in garbage_chars}
print(f"\nglyph_table entries with OCR garbage chars {garbage_chars}: {len(garbage)}")

# Check ksx1001-charmap at those positions
ks_at_garbage = [(k, v, ks.get(k)) for k,v in garbage.items() if ks.get(k)]
print(f"Of those, {len(ks_at_garbage)} have ksx1001 entries")
print("First 20:")
for k, gt_v, ks_v in ks_at_garbage[:20]:
    print(f"  {k}: gt={gt_v!r} ks={ks_v!r}")
