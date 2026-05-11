#!/usr/bin/env python3
"""Round-10 sentence-context labels (second agent-driven batch).

Three more general-purpose agents read every remaining unknown codepoint
(354 cps split into 3 chunks by frequency: 118 high-freq+broken-cluster,
118 mid-freq with sparse context, 118 single-occurrence). The skip lists
explicitly pre-flagged the LIS-broken cluster from round 9 so agents
focused effort on tractable cps.

Returned: 8 / 20 / 62 = 90 raw proposals. 1 rejected at merge for
violating LIS bracket (0x3A4E -> 멧 outside bracket — agent saw "헬멧"
in context but bracket allowed only 맷/매/맹). 89 net-new labels applied.
"""
from __future__ import annotations
import json
from pathlib import Path

ROUND10 = {
    "3704": '갇',
    "3717": '갬',
    "371B": '갱',
    "377F": '굽',
    "379A": '긁',
    "379D": '긋',
    "37B7": '깥',
    "37C8": '껄',
    "37E3": '꽁',
    "380C": '꿉',
    "3822": '끅',
    "3831": '낌',
    "386C": '녁',
    "3898": '눕',
    "38AF": '늠',
    "38BE": '닙',
    "38C8": '닭',
    "38DB": '댔',
    "38E3": '덜',
    "3922": '됨',
    "392F": '뒀',
    "3955": '딴',
    "3998": '뜯',
    "39A2": '띠',
    "39AC": '랄',
    "39AF": '랏',
    "39B3": '랖',
    "39C2": '량',
    "39CA": '렀',
    "39DB": '렷',
    "39E5": '롤',
    "39E6": '롬',
    "3A0E": '룬',
    "3A47": '맣',
    "3A49": '맥',
    "3A51": '맺',
    "3A7A": '몹',
    "3AB6": '밌',
    "3AB7": '밍',
    "3AB8": '및',
    "3AC8": '밭',
    "3ACB": '밴',
    "3ACC": '밸',
    "3B01": '볍',
    "3B43": '빈',
    "3B54": '빴',
    "3B64": '뻑',
    "3B80": '뿍',
    "3B8A": '쁨',
    "3B8B": '쁨',
    "3B9C": '삶',
    "3BA5": '샌',
    "3BCC": '셈',
    "3BD4": '셜',
    "3BEE": '쇄',
    "3C1F": '숴',
    "3C2A": '쉼',
    "3C31": '슐',
    "3C52": '쌓',
    "3C5F": '썰',
    "3C9C": '씹',
    "3CB2": '앨',
    "3CC2": '얗',
    "3CCD": '얽',
    "3CDE": '엣',
    "3D50": '윌',
    "3D53": '윗',
    "3D95": '쟁',
    "3E08": '즙',
    "3E31": '쩌',
    "3E32": '쩔',
    "3E7C": '챘',
    "3E89": '첩',
    "3E9E": '촐',
    "3ED9": '칭',
    "3EDC": '칸',
    "3EE4": '캔',
    "3EE7": '캡',
    "3EEB": '캬',
    "3F20": '콧',
    "3F5D": '탓',
    "3FA4": '튕',
    "3FBA": '틴',
    "3FBC": '팀',
    "400B": '폼',
    "403B": '학',
    "404E": '허',
    "4066": '혔',
    "40A0": '휙',
}

HERE = Path(__file__).resolve().parent
MAP = HERE / "codepoint_map.json"


def main():
    raw = json.load(open(MAP))
    before = len(raw)
    added, conflicts, violations = [], [], []
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
        prev_a, next_a = None, None
        for a in lis:
            if a[0] < cp:
                prev_a = a
            elif a[0] > cp and next_a is None:
                next_a = a
                break
        lo = (prev_a[2] + 1) if prev_a else 0xAC00
        hi = (next_a[2] - 1) if next_a else 0xD7A3
        return lo, hi

    for cp_hex, ch in sorted(ROUND10.items()):
        cp_hex = cp_hex.upper()
        if cp_hex in raw:
            if raw[cp_hex] != ch:
                conflicts.append((cp_hex, raw[cp_hex], ch))
            continue
        lo, hi = bracket(int(cp_hex, 16))
        if not (lo <= ord(ch) <= hi):
            violations.append((cp_hex, ch, lo, hi))
            continue
        raw[cp_hex] = ch
        added.append((cp_hex, ch))

    out_sorted = {k: raw[k] for k in sorted(raw, key=lambda h: int(h, 16))}
    MAP.write_text(json.dumps(out_sorted, indent=2, ensure_ascii=False) + "\n")
    print(f"before {before}, after {len(out_sorted)} (+{len(added)})")
    print(f"conflicts: {len(conflicts)}, violations: {len(violations)}")
    if violations:
        for v in violations[:10]:
            print(f"  VIOL {v[0]} {v[1]} not in U+{v[2]:04X}..U+{v[3]:04X}")


if __name__ == "__main__":
    main()
