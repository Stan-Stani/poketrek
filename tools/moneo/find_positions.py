#!/usr/bin/env python3
"""Find unknown char positions using ROM text context patterns."""
import json
from collections import Counter

with open('.moneo-artifacts/rom-text-ko-raw.json') as f:
    data = json.load(f)
records = data['records']

def get_korean_tokens(rec):
    """Extract list of (page_byte, idx_byte) for Korean syllable tokens."""
    result = []
    for t in rec.get('tokens', []):
        if t.get('k') == 'P' and isinstance(t.get('v'), list) and len(t['v']) == 2:
            pb, ib = t['v']
            if 0xF1 <= pb <= 0xF6:
                result.append((pb, ib))
    return result

# Known positions (page_byte, idx_byte) → char
known = {
    (0xF1, 102): '가', (0xF1, 178): '하', (0xF1, 91): '나', (0xF2, 38): '로',
    (0xF1, 26): '이', (0xF1, 168): '거', (0xF1, 108): '다', (0xF2, 44): '사',
    (0xF2, 174): '를', (0xF1, 70): '을', (0xF1, 3): '그',
}

# For each unknown char, find what token frequently co-occurs with known chars
# Tutorial: 상하좌우로 움직이거나 항목을 선택합니다。
# We know: 하=(F1,178), 로=(F2,38), 이=(F1,26?), 나=(F1,91)

# Strategy: find all records containing (F1,178)=하, and find what comes BEFORE 하
print("=== Chars appearing before 하 (F1,178) ===")
before_ha = Counter()
for rec in records:
    tokens = get_korean_tokens(rec)
    for i, t in enumerate(tokens):
        if t[0] == 0xF1 and t[1] == 178:  # 하
            if i > 0:
                prev = tokens[i-1]
                before_ha[(prev[0], prev[1])] += 1
top_before_ha = before_ha.most_common(10)
for (pb, ib), cnt in top_before_ha:
    ch = known.get((pb, ib), '?')
    print(f"  ({hex(pb)},{ib}) = '{ch}' : {cnt} times")

print("\n=== Chars appearing AFTER 하 (F1,178) ===")
after_ha = Counter()
for rec in records:
    tokens = get_korean_tokens(rec)
    for i, t in enumerate(tokens):
        if t[0] == 0xF1 and t[1] == 178:
            if i + 1 < len(tokens):
                nxt = tokens[i+1]
                after_ha[(nxt[0], nxt[1])] += 1
for (pb, ib), cnt in after_ha.most_common(10):
    ch = known.get((pb, ib), '?')
    print(f"  ({hex(pb)},{ib}) = '{ch}' : {cnt} times")

# Also: find chars before 로(F2,38) - tutorial has 우로
print("\n=== Chars appearing before 로 (F2,38) ===")
before_ro = Counter()
for rec in records:
    tokens = get_korean_tokens(rec)
    for i, t in enumerate(tokens):
        if t[0] == 0xF2 and t[1] == 38:
            if i > 0:
                prev = tokens[i-1]
                before_ro[(prev[0], prev[1])] += 1
for (pb, ib), cnt in before_ro.most_common(10):
    ch = known.get((pb, ib), '?')
    print(f"  ({hex(pb)},{ib}) = '{ch}' : {cnt} times")

# Find chars before 나(F1,91) - tutorial has 이거나
print("\n=== Chars appearing before 나 (F1,91) ===")
before_na = Counter()
for rec in records:
    tokens = get_korean_tokens(rec)
    for i, t in enumerate(tokens):
        if t[0] == 0xF1 and t[1] == 91:
            if i > 0:
                prev = tokens[i-1]
                before_na[(prev[0], prev[1])] += 1
for (pb, ib), cnt in before_na.most_common(10):
    ch = known.get((pb, ib), '?')
    print(f"  ({hex(pb)},{ib}) = '{ch}' : {cnt} times")

# Find chars before 이(F1,26) - tutorial has 직이거나
print("\n=== Chars appearing before 이 (F1,26) ===")
before_i = Counter()
for rec in records:
    tokens = get_korean_tokens(rec)
    for i, t in enumerate(tokens):
        if t[0] == 0xF1 and t[1] == 26:
            if i > 0:
                prev = tokens[i-1]
                before_i[(prev[0], prev[1])] += 1
for (pb, ib), cnt in before_i.most_common(10):
    ch = known.get((pb, ib), '?')
    print(f"  ({hex(pb)},{ib}) = '{ch}' : {cnt} times")

# Also find 을(F1,70) neighbors - tutorial has 항목을 선택합니다
print("\n=== Chars appearing BEFORE 을 (F1,70) ===")
before_ul = Counter()
for rec in records:
    tokens = get_korean_tokens(rec)
    for i, t in enumerate(tokens):
        if t[0] == 0xF1 and t[1] == 70:
            if i > 0:
                prev = tokens[i-1]
                before_ul[(prev[0], prev[1])] += 1
for (pb, ib), cnt in before_ul.most_common(10):
    ch = known.get((pb, ib), '?')
    print(f"  ({hex(pb)},{ib}) = '{ch}' : {cnt} times")

print("\n=== Chars appearing AFTER 을 (F1,70) ===")
after_ul = Counter()
for rec in records:
    tokens = get_korean_tokens(rec)
    for i, t in enumerate(tokens):
        if t[0] == 0xF1 and t[1] == 70:
            if i + 1 < len(tokens):
                nxt = tokens[i+1]
                after_ul[(nxt[0], nxt[1])] += 1
for (pb, ib), cnt in after_ul.most_common(10):
    ch = known.get((pb, ib), '?')
    print(f"  ({hex(pb)},{ib}) = '{ch}' : {cnt} times")
