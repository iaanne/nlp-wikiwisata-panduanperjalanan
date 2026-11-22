"""Create a geographically spread, one-source-per-question review set.

This is a candidate set, not human annotations or final qrels.
"""
import json
from pathlib import Path

from wikiwisata.corpus.chunking import chunk_article
from wikiwisata.corpus.parsing import parse_article

ROOT = Path(__file__).resolve().parents[1]
INDEX = json.loads((ROOT / 'data/indexes/index_manifest.json').read_text(encoding='utf-8'))
articles = [parse_article(json.loads(p.read_text(encoding='utf-8')))
            for p in (ROOT / 'data/snapshots').glob('*.json')]
articles.sort(key=lambda a: (a['title'].casefold(), a['revision_id']))
latest = {}
for article in articles:
    key = article['page_id']
    if key not in latest or article['revision_timestamp'] > latest[key]['revision_timestamp']:
        latest[key] = article
articles = list(latest.values())

def usable(a):
    for item, chunk in zip(a['listings'], chunk_article(a, 'listing')):
        if item.get('name') and len(item['name']) >= 4:
            fields = [(k, item[k]) for k in ('address', 'hours', 'price') if item.get(k)]
            if fields:
                return item, chunk, fields
    return None

def ask_field(key, name, destination):
    if key == 'address':
        return f'Di mana alamat {name} di {destination}?'
    if key == 'hours':
        return f'Jam berapa {name} di {destination} buka?'
    return f'Berapa harga masuk {name} di {destination}?'

def field_phrase(key):
    return {'address': 'di mana alamatnya', 'hours': 'jam berapa bukanya',
            'price': 'berapa biayanya'}[key]

listing_articles = [a for a in articles if usable(a) and a['title'] != 'Yogyakarta']
other_articles = [a for a in articles if not usable(a)]
other_articles = sorted(other_articles, key=lambda a: (a['page_id'] * 2654435761) % (2**32))
questions, candidates = [], []
used = set()

def put(slice_name, a, question, answer, chunks, note, answerable=True):
    assert a['page_id'] not in used
    used.add(a['page_id'])
    qid = f'q{len(questions)+1:03d}'
    questions.append({'id': qid, 'slice': slice_name, 'question': question,
                      'travel_date': '2026-11-22', 'answerable': answerable,
                      'draft_answer': answer, 'source_doc_id': a['doc_id'],
                      'source_title': a['title'], 'source_revision_id': a['revision_id'],
                      'corpus_hash': INDEX['corpus_hash'],
                      'annotation_status': 'needs_blind_review', 'review_note': note})
    for chunk in chunks:
        candidates.append({'question_id': qid, 'chunk_id': chunk['chunk_id'],
                           'source_doc_id': chunk['doc_id'], 'strategy': chunk['strategy'],
                           'proposed_relevance': 2, 'status': 'candidate_unverified',
                           'corpus_hash': INDEX['corpus_hash']})

# 45 direct questions, one article each.
for a in listing_articles:
    if len(questions) == 45:
        break
    item, chunk, fields = usable(a)
    key, value = fields[0]
    put('easy', a, ask_field(key, item['name'], a['title']),
        value, [chunk], 'Periksa nilai dan keunikan nama tempat.')

# 35 questions combining two fields, from 35 other articles.
for a in listing_articles:
    if sum(q['slice'] == 'multi_hop' for q in questions) == 35:
        break
    if a['page_id'] in used:
        continue
    item, chunk, fields = usable(a)
    if len(fields) < 2:
        continue
    (k1, v1), (k2, v2) = fields[:2]
    put('multi_hop', a,
        f'Kalau mau ke {item["name"]} di {a["title"]}, {field_phrase(k1)} dan {field_phrase(k2)}?',
        {k1: v1, k2: v2}, [chunk],
        'Dua fakta ada dalam satu passage; perlu diubah menjadi multi-hop sungguhan.')

# One actual paired-revision item, then revision-scoped candidates from distinct articles.
old = next(a for a in [parse_article(json.loads(p.read_text(encoding='utf-8')))
                     for p in (ROOT / 'data/snapshots').glob('2728_*.json')]
           if a['revision_id'] == '35263')
new = latest[old['page_id']]
old_chunks = chunk_article(old, 'section')
new_chunks = chunk_article(new, 'section')
put('temporal_conflict', new,
    'Kalau saya ke Yogyakarta akhir tahun ini, ada info wisata yang berubah belakangan ini?',
    None, old_chunks[:1] + new_chunks[:1],
    'Pasangan revisi nyata, tetapi passage dan jawaban wajib ditentukan manusia.')
for a in listing_articles:
    if sum(q['slice'] == 'temporal_conflict' for q in questions) == 25:
        break
    if a['page_id'] in used:
        continue
    item, chunk, fields = usable(a)
    key, value = fields[0]
    put('temporal_conflict', a,
        f'Kalau saya ke {a["title"]} akhir November 2026, {ask_field(key, item["name"], a["title"]).lower()}',
        value, [chunk], 'Hanya satu revisi tersedia; belum menguji konflik temporal.')

# Missing fields are candidate no-evidence questions only; all-passages check is required.
for a in listing_articles:
    if sum(q['slice'] == 'no_evidence' for q in questions) == 30:
        break
    if a['page_id'] in used:
        continue
    item, chunk, fields = usable(a)
    missing = next((k for k in ('price', 'hours', 'address') if not item.get(k)), None)
    if missing:
        put('no_evidence', a,
            ask_field(missing, item['name'], a['title']),
            None, [], 'Cek seluruh korpus; kolom kosong di satu listing belum membuktikan tidak ada bukti.', False)

# Remaining 15 questions from sections of distinct articles, extending geographic reach.
for a in other_articles + listing_articles:
    if len(questions) == 150:
        break
    if a['page_id'] in used:
        continue
    chunks = chunk_article(a, 'section')
    intro = next((c for c in chunks if c['text'] and len(c['text']) > 45), None)
    if intro:
        put('easy', a, f'Kalau mau ke {a["title"]}, apa yang perlu saya tahu tentang tempat itu?',
            None, [intro], 'Cek apakah passage menjelaskan jenis tempat dan cocok untuk pertanyaan wisatawan.')

assert len(questions) == 150, len(questions)
assert len({q['source_doc_id'].split(':')[0] for q in questions}) == 150
out = ROOT / 'data/benchmark'
for name, rows in [('questions_150.draft.jsonl', questions),
                   ('qrels_150_candidates.draft.jsonl', candidates)]:
    (out / name).write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in rows), encoding='utf-8')
print({s: sum(q['slice'] == s for q in questions) for s in
       ('easy', 'multi_hop', 'temporal_conflict', 'no_evidence')})
print('distinct source articles:', len(used), 'candidate passage links:', len(candidates))
