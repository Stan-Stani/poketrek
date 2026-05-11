#!/usr/bin/env python3
"""Visual-picker round 1: agents visually picked from PIL OCR top-8.

Round 10 hit a context-only ceiling. We then rendered every remaining
unknown's ROM glyph at 5x next to its PIL-OCR top-8 candidates and had
two agents (sheets 0-7, sheets 8-15) visually compare and pick.

Yield is low (24 / ~250 in-scope cps) because:
  - PIL's top-8 is itself noisy — the visually correct syllable family
    is often NOT in the candidate set (e.g. 0x3863 should be 넷 per
    corpus context but PIL never proposed it).
  - Many ROM "glyphs" in the singleton tier are control bytes / blank
    atlas slots (~10 confirmed in agent B's pass).
  - The hardest tier (LIS-broken cluster) was excluded from this pass
    because context-only reconciliation handles those better.

Output is sanity-checked: all 24 sit inside the current LIS bracket
(0 violations on apply). Future visual passes would benefit from
agent-driven candidate generation rather than relying on PIL.
"""
from __future__ import annotations
import json
from pathlib import Path

VISUAL_R1 = {
    "3782": '굿',
    "3793": '균',
    "3798": '귿',
    "37E7": '꽉',
    "385B": '넓',
    "3864": '넨',
    "39BE": '랴',
    "3A68": '멨',
    "3B42": '빅',
    "3B4E": '빤',
    "3B9F": '삿',
    "3CBE": '얍',
    "3CBF": '얐',
    "3D8C": '잦',
    "3DAB": '젝',
    "3E10": '짊',
    "3E8A": '첫',
    "3EE3": '캑',
    "3F30": '쿨',
    "3FE1": '펙',
    "404C": '햐',
    "4051": '헐',
    "4093": '훗',
    "40A2": '휠',
}

HERE = Path(__file__).resolve().parent
MAP = HERE / "codepoint_map.json"


def main():
    raw = json.load(open(MAP))
    before = len(raw)
    added, collide, viol = [], [], []
    anchors = sorted([(int(k, 16), v, ord(v)) for k, v in raw.items()])

    def lis_by_uni(a):
        n = len(a); dp = [1] * n; prev = [-1] * n
        for i in range(n):
            for j in range(i):
                if a[j][2] < a[i][2] and dp[j] + 1 > dp[i]:
                    dp[i] = dp[j] + 1
                    prev[i] = j
        end = max(range(n), key=lambda i: dp[i])
        seq = []
        while end != -1:
            seq.append(a[end])
            end = prev[end]
        return list(reversed(seq))

    lis = lis_by_uni(anchors)

    def bracket(cp):
        p, n = None, None
        for a in lis:
            if a[0] < cp:
                p = a
            elif a[0] > cp and n is None:
                n = a
                break
        return (p[2] + 1 if p else 0xAC00, n[2] - 1 if n else 0xD7A3)

    for cp_hex, ch in sorted(VISUAL_R1.items()):
        cp_hex = cp_hex.upper()
        if cp_hex in raw:
            if raw[cp_hex] != ch:
                collide.append((cp_hex, raw[cp_hex], ch))
            continue
        lo, hi = bracket(int(cp_hex, 16))
        if not (lo <= ord(ch) <= hi):
            viol.append((cp_hex, ch, lo, hi))
            continue
        raw[cp_hex] = ch
        added.append((cp_hex, ch))

    out_sorted = {k: raw[k] for k in sorted(raw, key=lambda h: int(h, 16))}
    MAP.write_text(json.dumps(out_sorted, indent=2, ensure_ascii=False) + "\n")
    print(f"before {before}, after {len(out_sorted)} (+{len(added)})")
    print(f"collisions: {len(collide)}, violations: {len(viol)}")


if __name__ == "__main__":
    main()
