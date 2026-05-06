import json
import os
from collections import Counter

BASE = '/Users/isolate/Developer/poketrek'
LEMMA_INDEX_PATH = os.path.join(BASE, 'tools/moneo/lemma_area_index.json')
VOCAB_TOPIC_PATH = os.path.join(BASE, 'app/src/main/assets/moneo/seed-vocab-ko-topik.json')
VOCAB_MINED_PATH = os.path.join(BASE, 'app/src/main/assets/moneo/seed-vocab-ko-mined.json')
SENT_TOPIC_PATH = os.path.join(BASE, 'app/src/main/assets/moneo/sentences-ko-topik.json')
SENT_MINED_PATH = os.path.join(BASE, 'app/src/main/assets/moneo/sentences-ko-mined.json')
OUT_VOCAB_TOPIC = os.path.join(BASE, 'tools/moneo/seed-vocab-ko-topik-attributed.json')
OUT_VOCAB_MINED = os.path.join(BASE, 'tools/moneo/seed-vocab-ko-mined-attributed.json')
OUT_SENT_TOPIC = os.path.join(BASE, 'tools/moneo/sentences-ko-topik-attributed.json')
OUT_SENT_MINED = os.path.join(BASE, 'tools/moneo/sentences-ko-mined-attributed.json')

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def attribute_vocab(vocab_path, lemma_index):
    data = load_json(vocab_path)
    entries = data['entries']
    attrib_map = {}
    area_counter = Counter()
    attributed = 0
    unattributed = 0
    for entry in entries:
        lemma = entry.get('korean')
        if lemma and lemma in lemma_index['lemmas']:
            info = lemma_index['lemmas'][lemma]
            entry['firstAreaEncountered'] = info['first_area']
            entry['areasReferenced'] = info['areas']
            entry['liveRecIds'] = info['rec_ids']
            attributed += 1
            area_counter[info['first_area']] += 1
            # Build map for sentence lookup using vocab id if present, else korean
            key = entry.get('id') if 'id' in entry else entry.get('korean')
            if key:
                attrib_map[key] = {
                    'firstAreaEncountered': info['first_area'],
                    'areasReferenced': info['areas'],
                    'liveRecIds': info['rec_ids']
                }
        else:
            unattributed += 1
    # Update notes
    if not isinstance(data.get('notes'), list):
        data['notes'] = [data['notes']] if data.get('notes') else []
    data['notes'].append(f'Attributed area data from lemma_area_index.json; {attributed} attributed, {unattributed} unattributed.')
    return data, attrib_map, area_counter, attributed, unattributed

def attribute_sentences(sent_path, attrib_map):
    data = load_json(sent_path)
    entries = data['entries']
    attributed = 0
    unattributed = 0
    for sent in entries:
        # Try vocabId parsed-lemma first (it always carries the lemma even
        # when targetForm is the conjugated surface form), then targetForm
        # (works for TOPIK where targetForm == lemma), then korean as a
        # last resort.
        candidates = []
        vid = sent.get('vocabId', '')
        if ':' in vid:
            candidates.append(vid.split(':', 1)[1])
        if sent.get('targetForm'):
            candidates.append(sent['targetForm'])
        if sent.get('korean'):
            candidates.append(sent['korean'])
        matched_key = next((k for k in candidates if k in attrib_map), None)
        if matched_key:
            sent['firstAreaEncountered'] = attrib_map[matched_key]['firstAreaEncountered']
            sent['areasReferenced'] = attrib_map[matched_key].get('areasReferenced', [])
            attributed += 1
        else:
            unattributed += 1
    if not isinstance(data.get('notes'), list):
        data['notes'] = [data['notes']] if data.get('notes') else []
    data['notes'].append(f'Sentence attribution via vocab map; {attributed} attributed, {unattributed} unattributed.')
    return data, attributed, unattributed

def print_stats(deck_name, total, attributed, unattributed, area_counter):
    print(f'{deck_name}:')
    print(f'  Cards: {total}')
    print(f'  Attributed: {attributed}')
    print(f'  Unattributed: {unattributed}')
    print('  Top 5 areas:')
    for area, count in area_counter.most_common(5):
        print(f'    {area}: {count}')

def main():
    lemma_index = load_json(LEMMA_INDEX_PATH)

    # Process vocab decks
    topic_vocab, topic_map, topic_area_count, topic_attr, topic_unattr = attribute_vocab(VOCAB_TOPIC_PATH, lemma_index)
    save_json(topic_vocab, OUT_VOCAB_TOPIC)
    print_stats('seed-vocab-ko-topik', len(topic_vocab['entries']), topic_attr, topic_unattr, topic_area_count)

    mined_vocab, mined_map, mined_area_count, mined_attr, mined_unattr = attribute_vocab(VOCAB_MINED_PATH, lemma_index)
    save_json(mined_vocab, OUT_VOCAB_MINED)
    print_stats('seed-vocab-ko-mined', len(mined_vocab['entries']), mined_attr, mined_unattr, mined_area_count)

    # Process sentences
    topic_sent, topic_sent_attr, topic_sent_unattr = attribute_sentences(SENT_TOPIC_PATH, topic_map)
    save_json(topic_sent, OUT_SENT_TOPIC)
    print_stats('sentences-ko-topik', len(topic_sent['entries']), topic_sent_attr, topic_sent_unattr, Counter())

    mined_sent, mined_sent_attr, mined_sent_unattr = attribute_sentences(SENT_MINED_PATH, mined_map)
    save_json(mined_sent, OUT_SENT_MINED)
    print_stats('sentences-ko-mined', len(mined_sent['entries']), mined_sent_attr, mined_sent_unattr, Counter())

if __name__ == '__main__':
    main()