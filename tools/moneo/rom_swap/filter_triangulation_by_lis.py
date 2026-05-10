#!/usr/bin/env python3
"""Filter codepoint_suggestions_2024.json against the LIS bracket
constraint. A predicted syllable for storage cp X is only valid if it
falls within the Unicode collation window bracketed by X's nearest
LIS anchors. n-gram triangulation has high false-positive rates for
common syllables (e.g. 있) -- this filter eliminates predictions that
violate the atlas's known monotonic structure.

Output: codepoint_suggestions_filtered.json with two lists:
  - validated: predictions whose syllable fits the LIS window
  - rejected: predictions outside the window (with the actual valid range)
"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
KNOWN = HERE / "codepoint_map.json"
SUGG = HERE.parent / "codepoint_suggestions_2024.json"
OUT  = HERE.parent / "codepoint_suggestions_filtered.json"

HANGUL_LO = 0xAC00
HANGUL_HI = 0xD7A3


def lis_by_unicode(anchors):
    n = len(anchors)
    if n == 0: return []
    dp = [1] * n
    prev = [-1] * n
    for i in range(n):
        for j in range(i):
            if anchors[j][2] < anchors[i][2] and dp[j] + 1 > dp[i]:
                dp[i] = dp[j] + 1
                prev[i] = j
    end = max(range(n), key=lambda i: dp[i])
    seq = []
    while end != -1:
        seq.append(anchors[end])
        end = prev[end]
    return list(reversed(seq))


def main():
    raw = json.load(open(KNOWN))
    sugg = json.load(open(SUGG))

    anchors = sorted([(int(k, 16), v, ord(v)) for k, v in raw.items()])
    lis = lis_by_unicode(anchors)

    def find_brackets(cp):
        prev_a, next_a = None, None
        for a in lis:
            if a[0] < cp:
                prev_a = a
            elif a[0] > cp and next_a is None:
                next_a = a; break
        lo = (prev_a[2] + 1) if prev_a else HANGUL_LO
        hi = (next_a[2] - 1) if next_a else HANGUL_HI
        return prev_a, next_a, lo, hi

    validated = []
    rejected = []
    for s in sugg["suggestions"]:
        cp = int(s["codepoint"][2:], 16)
        cp_hex = s["codepoint"][2:]
        pred = s["predicted"]
        prev_a, next_a, lo, hi = find_brackets(cp)
        pred_uni = ord(pred)
        in_range = lo <= pred_uni <= hi
        entry = dict(s)
        entry["lo_uni"] = f"U+{lo:04X}"
        entry["hi_uni"] = f"U+{hi:04X}"
        entry["prev_anchor"] = (f"0x{prev_a[0]:04X}", prev_a[1]) if prev_a else None
        entry["next_anchor"] = (f"0x{next_a[0]:04X}", next_a[1]) if next_a else None
        entry["bracket_size"] = hi - lo + 1
        if in_range:
            validated.append(entry)
        else:
            rejected.append(entry)

    print(f"validated: {len(validated)}")
    print(f"rejected:  {len(rejected)}")
    print()
    print("validated (predicted syllable fits LIS window):")
    for e in sorted(validated, key=lambda x: -x["occurrences"]):
        print(f"  cp 0x{e['codepoint'][2:]} -> {e['predicted']!r}  "
              f"(margin {e['margin']}, {e['occurrences']} occ, "
              f"bracket {e['bracket_size']})")
    print()
    print("rejected (predicted outside LIS window):")
    for e in rejected:
        print(f"  cp 0x{e['codepoint'][2:]} -> {e['predicted']!r}  "
              f"window {e['lo_uni']}..{e['hi_uni']} "
              f"(predicted U+{ord(e['predicted']):04X})")

    OUT.write_text(json.dumps({
        "version": 1,
        "method": "n-gram triangulation filtered by LIS bracket constraint",
        "stats": {
            "total_suggestions": len(sugg["suggestions"]),
            "validated": len(validated),
            "rejected": len(rejected),
        },
        "validated": validated,
        "rejected": rejected,
    }, indent=2, ensure_ascii=False))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
