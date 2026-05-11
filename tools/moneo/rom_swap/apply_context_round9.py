#!/usr/bin/env python3
"""Round-9 sentence-context labels (agent-driven batch).

Three general-purpose agents read the corpus context for every unknown
codepoint with >=3 occurrences (458 cps total across three chunks),
proposed labels from the LIS-bracketed candidate set per cp, and
returned merged JSON. 299 net-new labels survived merge + LIS
verification (0 conflicts between agents, 0 bracket violations).
"""
from __future__ import annotations
import json
from pathlib import Path

ROUND9 = {
    "3726": '걱',
    "3728": '걷',
    "3731": '겉',
    "3735": '겐',
    "3745": '겼',
    "3746": '경',
    "3748": '계',
    "374E": '곡',
    "3750": '곧',
    "3756": '곱',
    "3764": '괜',
    "3777": '국',
    "3779": '굳',
    "3792": '규',
    "3796": '극',
    "37A2": '긴',
    "37A7": '깁',
    "37AB": '깊',
    "37AE": '깎',
    "37AF": '깐',
    "37B0": '깔',
    "37B3": '깝',
    "37C6": '꺾',
    "37CE": '께',
    "37DC": '꼭',
    "37DF": '꼴',
    "37E0": '꼼',
    "37E1": '꼽',
    "37E4": '꽂',
    "37EB": '꽤',
    "3808": '꾼',
    "3810": '꿔',
    "381C": '뀐',
    "3821": '끄',
    "3823": '끈',
    "3824": '끊',
    "3825": '끌',
    "382A": '끗',
    "382C": '끝',
    "3836": '낙',
    "383B": '낡',
    "383E": '납',
    "383F": '낫',
    "3840": '났',
    "3842": '낮',
    "3848": '낸',
    "3849": '낼',
    "384B": '냅',
    "384D": '냈',
    "384F": '냐',
    "3854": '냥',
    "3858": '넌',
    "385C": '넘',
    "386D": '년',
    "3871": '녔',
    "3872": '녕',
    "387F": '높',
    "3880": '놓',
    "3885": '뇌',
    "3896": '눌',
    "389B": '눠',
    "389C": '뉜',
    "38A3": '뉴',
    "38A9": '느',
    "38B3": '늦',
    "38B5": '늬',
    "38BB": '닐',
    "38C0": '닝',
    "38C6": '닫',
    "38C9": '닮',
    "38CC": '담',
    "38CD": '답',
    "38CE": '닷',
    "38D3": '닿',
    "38D9": '댑',
    "38E6": '덤',
    "38EB": '덮',
    "391D": '돼',
    "3921": '될',
    "3923": '됩',
    "3929": '둘',
    "392B": '둡',
    "392E": '둬',
    "3936": '뒷',
    "3940": '듣',
    "3943": '듬',
    "3944": '듭',
    "3945": '듯',
    "3951": '딩',
    "3952": '딪',
    "3956": '딸',
    "3957": '땀',
    "3966": '떠',
    "3967": '떡',
    "396F": '떴',
    "397E": '똑',
    "3981": '똥',
    "3996": '뜩',
    "3997": '뜬',
    "399C": '뜻',
    "39AE": '랍',
    "39B0": '랐',
    "39B4": '랗',
    "39B9": '램',
    "39BB": '랫',
    "39BC": '랬',
    "39BD": '랭',
    "39BF": '략',
    "39C6": '럴',
    "39C8": '럽',
    "39CB": '렁',
    "39CF": '렌',
    "39D8": '렬',
    "39DA": '렵',
    "39DD": '령',
    "39E4": '론',
    "39E7": '롭',
    "39E8": '롯',
    "3A0D": '룩',
    "3A0F": '룰',
    "3A10": '룸',
    "3A11": '룹',
    "3A14": '뤄',
    "3A21": '률',
    "3A25": '륭',
    "3A27": '륵',
    "3A2B": '릅',
    "3A36": '립',
    "3A3F": '맑',
    "3A41": '맘',
    "3A42": '맙',
    "3A43": '맛',
    "3A4D": '맵',
    "3A5B": '멈',
    "3A65": '멤',
    "3A69": '멩',
    "3A71": '몇',
    "3A77": '몰',
    "3A87": '묘',
    "3A90": '묻',
    "3A96": '뭇',
    "3A9A": '뭐',
    "3A9B": '뭔',
    "3AA8": '므',
    "3AAF": '민',
    "3AB0": '믿',
    "3AB9": '밑',
    "3AC4": '밤',
    "3ACA": '백',
    "3AE6": '벨',
    "3AEC": '벼',
    "3B05": '볕',
    "3B0D": '봄',
    "3B0E": '봅',
    "3B13": '봤',
    "3B23": '붉',
    "3B29": '붙',
    "3B34": '뷰',
    "3B48": '빗',
    "3B4D": '빡',
    "3B4F": '빨',
    "3B57": '빼',
    "3B7D": '뾰',
    "3B81": '뿐',
    "3B89": '쁜',
    "3B96": '삭',
    "3BA0": '샀',
    "3BC3": '섭',
    "3BCA": '센',
    "3BCE": '셋',
    "3BD3": '션',
    "3BD8": '셨',
    "3C05": '쇠',
    "3C10": '숍',
    "3C14": '숙',
    "3C1E": '숲',
    "3C2C": '쉽',
    "3C37": '슨',
    "3C3C": '슷',
    "3C46": '싯',
    "3C51": '쌍',
    "3C5C": '써',
    "3C63": '썼',
    "3C65": '쎄',
    "3C8B": '쓰',
    "3C8D": '쓴',
    "3C91": '씀',
    "3C99": '씬',
    "3CAC": '앙',
    "3CBD": '얌',
    "3CC1": '얕',
    "3CC3": '얘',
    "3CCB": '얻',
    "3CDA": '엔',
    "3CEE": '옆',
    "3D0D": '옮',
    "3D11": '옵',
    "3D17": '완',
    "3D1E": '왜',
    "3D20": '왜',
    "3D24": '외',
    "3D26": '왼',
    "3D35": '욱',
    "3D41": '월',
    "3D44": '웠',
    "3D47": '웩',
    "3D58": '율',
    "3D5F": '윽',
    "3D64": '읍',
    "3D66": '응',
    "3D73": '익',
    "3D76": '읽',
    "3D78": '잃',
    "3D7E": '잊',
    "3D83": '잖',
    "3DA4": '젊',
    "3DAD": '젤',
    "3DBC": '존',
    "3DBD": '졸',
    "3DC6": '좌',
    "3DCF": '죄',
    "3DD6": '죠',
    "3DE0": '줌',
    "3DE1": '줍',
    "3DE4": '줘',
    "3DE5": '줘',
    "3E06": '즐',
    "3E07": '즘',
    "3E0A": '증',
    "3E11": '짐',
    "3E14": '징',
    "3E18": '짜',
    "3E19": '짝',
    "3E1D": '짧',
    "3E22": '짱',
    "3E64": '찔',
    "3E6C": '찬',
    "3E6D": '찮',
    "3E6E": '찰',
    "3E72": '찼',
    "3E73": '창',
    "3E76": '책',
    "3E85": '척',
    "3E97": '쳤',
    "3E9C": '촉',
    "3E9D": '촌',
    "3EB2": '춘',
    "3EB8": '춰',
    "3EB9": '췄',
    "3EC9": '측',
    "3ECF": '층',
    "3ED1": '칙',
    "3EDE": '캄',
    "3EE6": '캠',
    "3EEE": '커',
    "3F01": '컨',
    "3F04": '컴',
    "3F17": '켰',
    "3F4B": '큼',
    "3F50": '킨',
    "3F53": '킵',
    "3F5C": '탑',
    "3F5E": '탔',
    "3F64": '탬',
    "3F6C": '턱',
    "3F77": '텐',
    "3F78": '텔',
    "3F79": '템',
    "3F87": '톱',
    "3FB0": '틈',
    "3FBF": '팅',
    "3FCC": '패',
    "3FEA": '펼',
    "3FEE": '평',
    "3FEF": '폐',
    "4010": '표',
    "4016": '푹',
    "4017": '푼',
    "4026": '퓨',
    "405B": '헴',
    "4061": '현',
    "406D": '혹',
    "4077": '확',
    "4079": '활',
    "407B": '황',
    "407F": '활',
    "408F": '훈',
    "4090": '훌',
    "4092": '훔',
    "4097": '훨',
    "40A4": '휩',
    "40A7": '휴',
    "40AE": '흐',
    "40B3": '흘',
    "40B5": '흠',
    "40B8": '흥',
    "40B9": '흩',
    "40C2": '힌',
    "40C3": '힐',
}

HERE = Path(__file__).resolve().parent
MAP = HERE / "codepoint_map.json"


def main():
    raw = json.load(open(MAP))
    new = ROUND9
    before = len(raw)
    added, conflicts, violations = [], [], []
    # Build LIS so we can re-verify every entry against current state
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

    for cp_hex, ch in sorted(new.items()):
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
