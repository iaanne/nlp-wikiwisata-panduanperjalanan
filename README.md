# Korpus dan retrieval WikiWisata

Pipeline ini mengambil revisi MediaWiki, menyimpan snapshot mentah yang dapat diaudit, mem-parsing templat senarai, membuat tiga bentuk chunk, dan menjalankan ablation A1/A2/A6/A7.

## Mulai

1. Salin `config.example.json` menjadi `config.json`.
2. Pastikan `api_url` adalah endpoint API sumber yang benar. Contoh yang disertakan memakai API Wikivoyage Indonesia; ganti bila tugas merujuk ke API WikiWisata lain.
3. Isi `articles` dengan judul dan kota. Untuk artikel konflik, isi `conflict_revision_ids` dengan dua revision ID yang akan diambil selain revisi terkini.
4. Buat `data/queries.json` berupa daftar seperti:

   ```json
   [
     {"id": "q1", "query": "tempat makan murah", "city": "Yogyakarta", "category": "eat"}
   ]
   ```

5. Siapkan Python 3.10+ lalu pasang dependensi `pip install -r requirements.txt`.
6. Jalankan berurutan dari folder proyek:

   ```powershell
   python -m wikiwisata_pipeline.cli fetch
   python -m wikiwisata_pipeline.cli build
   python -m wikiwisata_pipeline.cli index
   python -m wikiwisata_pipeline.cli experiments
   ```

Model embedding dan reranker berjalan lokal melalui Sentence Transformers. Unduhan model pertama kali memerlukan akses jaringan. Untuk mengulang eksperimen dengan korpus/model sama, pertahankan snapshot, konfigurasi, dan file indeks.

## Artefak

- `data/snapshots/*.json`: respons API lengkap, wikitext, waktu pengambilan, revision ID/timestamp, dan SHA-256 wikitext.
- `data/source_register.jsonl`: URL sumber, waktu pengambilan, revision ID, hash, dan snapshot.
- `data/articles.jsonl`, `data/chunks_{fixed,section,listing}.jsonl`.
- `data/usage_counts.csv`: jumlah dokumen, butir senarai yang terpakai, dan chunk per strategi.
- `data/indexes/`: salinan chunk, vektor dense, model, dan hash indeks.
- `data/retrieval_cache.jsonl`: cache hasil `Retriever.search`, dikunci oleh hash indeks dan parameter pencarian.
- `data/retrieval_runs.jsonl`: hasil varian eksperimen.

`Retriever` menyediakan `search(...)` dan `index_hash()`. Filter `city` dan `category` diterapkan sebelum pemeringkatan; pada chunk senarai, kategori berasal dari templat (misalnya `eat` atau `see`).

## Definisi ablation

- **A1**: hybrid retrieval pada chunk `fixed`, `section`, dan `listing`.
- **A2**: dense (multilingual E5), BM25, hybrid reciprocal-rank fusion, dan hybrid + cross-encoder reranker.
- **A6**: kebijakan fixed top-k dibanding adaptive; adaptive mulai dari 3 hasil dan memperluas hingga 2× top-k bila skor fusion teratas di bawah ambang konfigurasi (default 0,025).
- **A7**: hasil retrieval yang sama dipotong menjadi dua budget konteks dalam hitungan kata. Ini proksi token yang konsisten tanpa tokenizer model generatif.

Jalankan `python -m unittest discover -s tests` untuk pengujian parser, metadata chunk, filter BM25, cache, dan validasi kueri.
