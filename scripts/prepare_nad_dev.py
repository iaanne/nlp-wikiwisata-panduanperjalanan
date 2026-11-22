"""Prepare a provisional dev split and fixed-chunk blind annotation packet.

No relevance labels are assigned here. Review/freeze questions before final qrels.
"""
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

from wikiwisata.corpus.chunking import chunk_article
from wikiwisata.corpus.parsing import parse_article

root = Path(__file__).resolve().parents[1]
bench = root / 'data/benchmark'
question_path = bench / 'questions_150.draft.jsonl'
questions = [json.loads(line) for line in question_path.read_text(encoding='utf-8').splitlines()]
assert len(questions) == 150
by_slice = defaultdict(list)
for q in questions:
    by_slice[q['slice']].append(q)

# Deterministic spread over each slice; 25 dev questions with every slice present.
targets = {'easy': 8, 'multi_hop': 7, 'temporal_conflict': 7, 'no_evidence': 3}
dev = []
for slice_name, count in targets.items():
    rows = sorted(by_slice[slice_name], key=lambda q: hashlib.sha256(q['id'].encode()).hexdigest())
    assert len(rows) >= count, (slice_name, len(rows))
    dev.extend(rows[:count])
dev.sort(key=lambda q: q['id'])
test = [q for q in questions if q['id'] not in {x['id'] for x in dev}]
assert len(dev) == 25 and len(test) == 125
assert not ({q['source_doc_id'].split(':')[0] for q in dev} &
            {q['source_doc_id'].split(':')[0] for q in test})

digest = hashlib.sha256(question_path.read_bytes()).hexdigest()
split = {'status': 'provisional_do_not_tune_final', 'question_file': question_path.name,
         'question_sha256': digest, 'split_unit': 'page_id',
         'dev_ids': [q['id'] for q in dev], 'test_ids': [q['id'] for q in test],
         'dev_slice_counts': dict(Counter(q['slice'] for q in dev)),
         'test_slice_counts': dict(Counter(q['slice'] for q in test))}
(bench / 'split.draft.json').write_text(json.dumps(split, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(bench / 'questions_dev.draft.jsonl').write_text(
    ''.join(json.dumps(q, ensure_ascii=False) + '\n' for q in dev), encoding='utf-8')

articles = {}
for path in (root / 'data/snapshots').glob('*.json'):
    article = parse_article(json.loads(path.read_text(encoding='utf-8')))
    articles[article['doc_id']] = article

def words(value):
    return set(re.findall(r'\w+', str(value).casefold()))

packet = []
for q in dev:
    article = articles[q['source_doc_id']]
    chunks = chunk_article(article, 'fixed')
    query_words = words(q['question']) | words(q.get('draft_answer') or '')
    ranked = sorted(chunks, key=lambda c: (-len(words(c['text']) & query_words), c['chunk_id']))
    chosen = ranked[:3]
    if q['slice'] == 'temporal_conflict' and article['title'] == 'Yogyakarta':
        previous = articles.get('2728:35263')
        if previous:
            chosen += chunk_article(previous, 'fixed')[:2]
    # Add an unrelated passage so both annotators can use label 0.
    distractor = next(a for a in articles.values() if a['page_id'] != article['page_id'] and a['title'] != article['title'])
    chosen += chunk_article(distractor, 'fixed')[:1]
    for c in chosen:
        packet.append({'question_id': q['id'], 'question': q['question'], 'slice': q['slice'],
                       'chunk_id': c['chunk_id'], 'doc_id': c['doc_id'],
                       'revision_id': c['revision_id'], 'chunking': 'fixed',
                       'text': c['text'], 'relevance': None,
                       'annotation_status': 'unlabeled'})

random.Random(20261122).shuffle(packet)
(bench / 'annotation_packet_dev.draft.jsonl').write_text(
    ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in packet), encoding='utf-8')
print('dev:', len(dev), 'test:', len(test), 'passages:', len(packet), 'slices:', split['dev_slice_counts'])
