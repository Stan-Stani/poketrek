#!/usr/bin/env python3
"""Bulk add labels to glyph-map.json.

Usage:
  python3 tools/moneo/add_labels.py F2,241=맥 F2,242=맨 ...
"""
import json
import sys
from pathlib import Path

GMAP = Path(__file__).resolve().parent / "glyph-map.json"


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: add_labels.py F<p>,<i>=<char> ...", file=sys.stderr)
        return 1
    doc = json.loads(GMAP.read_text(encoding="utf-8"))
    labels = doc["map"]
    added, replaced = 0, 0
    for arg in args:
        if "=" not in arg:
            print(f"skip (no '='): {arg}", file=sys.stderr); continue
        key, val = arg.split("=", 1)
        key = key.strip(); val = val.strip()
        if key in labels:
            old = labels[key]
            if old == val:
                print(f"  {key} = {val} (unchanged)")
                continue
            print(f"  {key} : {old} → {val}")
            replaced += 1
        else:
            print(f"  {key} = {val} (new)")
            added += 1
        labels[key] = val
    doc["map"] = dict(sorted(labels.items(),
                              key=lambda kv: tuple(int(x) for x in kv[0][1:].split(","))))
    GMAP.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{added} added, {replaced} replaced. Total: {len(labels)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
