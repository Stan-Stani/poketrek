#!/usr/bin/env python3
"""Inspect partial capture-bp3.json."""
import json
from collections import Counter

c = json.load(open('.moneo-artifacts/capture-bp3.json'))
toks = c['tokens']
print('tokens:', len(toks))
unique = set((t['page'], t['idx']) for t in toks)
print('unique (page,idx):', len(unique))
if toks:
    print('frame range:', min(t['frame'] for t in toks), '..', max(t['frame'] for t in toks))
pg = Counter(t['page'] for t in toks)
print('pages:', dict(pg))
sp = Counter(t['strptr'] for t in toks)
print('unique strptr:', len(sp), 'top 5:', sp.most_common(5))
