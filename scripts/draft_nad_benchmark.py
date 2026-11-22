"""Draft corpus-grounded questions and evidence candidates; human review required."""
import json
from pathlib import Path

from wikiwisata.corpus.chunking import chunk_article
from wikiwisata.corpus.parsing import parse_article

root = Path(__file__).resolve().parents[1]
articles = []
for path in sorted((root / "data/snapshots").glob("*.json")):
    article = parse_article(json.loads(path.read_text(encoding="utf-8")))
    if article["listings"]:
        articles.append(article)

questions = []
qrels = []
seen = set()

def add(slice_name, text, article, chunks, answerable, answer, evidence, note):
    if text in seen:
        return
    seen.add(text)
    qid = f"q{len(questions)+1:03d}"
    questions.append({"id": qid, "slice": slice_name, "question": text,
                      "travel_date": "2026-11-22", "answerable": answerable,
                      "draft_answer": answer, "source_doc_id": article["doc_id"],
                      "annotation_status": "needs_blind_review", "review_note": note})
    for chunk in evidence:
        qrels.append({"question_id": qid, "chunk_id": chunk["chunk_id"],
                      "relevance": 2, "status": "candidate_unverified",
                      "source_doc_id": article["doc_id"]})

for article in articles:
    chunks = chunk_article(article, "listing")
    for item, chunk in zip(article["listings"], chunks):
        name = item.get("name")
        if not name or len(name) < 4:
            continue
        for field, label in (("address", "alamat"), ("hours", "jam buka"), ("price", "harga")):
            value = item.get(field)
            if value and len([q for q in questions if q["slice"] == "easy"]) < 30:
                add("easy", f"Apa {label} {name} menurut artikel {article['title']}?", article,
                    chunks, True, value, [chunk], "Cek bahwa nilai di passage menjawab pertanyaan.")
        fields = [(key, item[key]) for key in ("address", "hours", "price") if item.get(key)]
        if len(fields) >= 2 and len([q for q in questions if q["slice"] == "multi_hop"]) < 35:
            a, b = fields[:2]
            add("multi_hop", f"Apa {a} dan {b} {name} menurut artikel {article['title']}?", article,
                chunks, True, {a[0]: a[1], b[0]: b[1]}, [chunk],
                "Dua fakta ada dalam satu listing; tinjau apakah memenuhi definisi multi-hop brief.")
        if not item.get("price") and len([q for q in questions if q["slice"] == "no_evidence"]) < 30:
            add("no_evidence", f"Berapa harga tiket {name} yang berlaku pada 22 November 2026 menurut artikel {article['title']}?",
                article, chunks, False, None, [],
                "Ketiadaan harga di listing ini belum membuktikan seluruh korpus tidak punya bukti; cek lintas passage.")
        if all(sum(q["slice"] == s for q in questions) >= n for s, n in
               (("easy", 30), ("multi_hop", 35), ("no_evidence", 30))):
            break
    if all(sum(q["slice"] == s for q in questions) >= n for s, n in
           (("easy", 30), ("multi_hop", 35), ("no_evidence", 30))):
        break

old = next(a for a in articles if a["doc_id"] == "2728:35263")
new = next(a for a in articles if a["doc_id"] == "2728:38824")
for article in (old, new):
    chunks = chunk_article(article, "listing")
    for item, chunk in zip(article["listings"], chunks):
        for field, label in (("address", "alamat"), ("hours", "jam buka"), ("price", "harga")):
            if not item.get(field) or sum(q["slice"] == "temporal_conflict" for q in questions) >= 25:
                continue
            add("temporal_conflict",
                f"Menurut revisi {article['revision_id']} artikel Yogyakarta, apa {label} {item['name']}?",
                article, chunks, True, item[field], [chunk],
                "Pertanyaan berbasis revisi; tinjau ulang agar menguji konflik temporal nyata.")

counts = {s: sum(q["slice"] == s for q in questions) for s in
          ("easy", "multi_hop", "temporal_conflict", "no_evidence")}
assert counts == {"easy": 30, "multi_hop": 35, "temporal_conflict": 25, "no_evidence": 30}, counts
out = root / "data/benchmark"
for filename, rows in (("questions_120.draft.jsonl", questions), ("qrels_candidates.draft.jsonl", qrels)):
    (out / filename).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
print(counts, "candidate qrels", len(qrels))
