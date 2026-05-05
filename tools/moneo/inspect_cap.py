#!/usr/bin/env python3
import json
from collections import Counter

c = json.load(open('.moneo-artifacts/capture-long2.json'))
print('keys:', list(c.keys()))
toks = c.get('tokens') or c.get('hits') or []
print('count:', len(toks))
print('first 3:', toks[:3] if toks else 'empty')
r0 = Counter()
pg = Counter()
ix = Counter()
for t in toks:
    if 'r0' in t:
        r0[t['r0']] += 1
    pg[t.get('page')] += 1
    ix[t.get('idx')] += 1
print('top r0:', r0.most_common(10))
print('top pages:', pg.most_common(10))
print('idx range:', (min(ix) if ix else None, max(ix) if ix else None), 'uniq=', len(ix))
