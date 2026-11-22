# Korpus dan retrieval WikiWisata

Pipeline mengambil revisi MediaWiki, menyimpan snapshot mentah yang dapat diaudit, mem-parsing templat senarai, membuat tiga bentuk chunk, dan menjalankan ablation A1/A2/A6/A7.

## Mulai

1. Pastikan Python 3.12 tersedia.
2. Sinkronkan environment dengan `uv sync`.
3. Daftar awal 320 halaman kandidat non-redirect dapat dibuat dengan `uv run python scripts/fetch_destinations.py`. Daftar ini berasal dari semua halaman Wikivoyage, bukan kurasi destinasi; tinjau judul dan nilai `city` di `configs/pipeline.yaml` sebelum fetch.
4. Untuk pasangan revisi Yogyakarta, konfigurasi memakai revision `35263` dan `38824` sebagai kandidat. Anotasikan section yang benar-benar berkonflik di `data/conflict_pairs.csv` setelah membandingkan isinya.
5. Buat/periksa `data/queries.json` sebagai daftar kueri benchmark.
6. Jalankan berurutan dari folder proyek:

   ```powershell
   uv run python -m wikiwisata.cli fetch
   uv run python -m wikiwisata.cli build
   uv run python -m wikiwisata.cli index
   uv run python -m wikiwisata.cli experiments
   ```

Model embedding dan reranker berjalan lokal melalui Sentence Transformers. Unduhan model pertama kali memerlukan akses jaringan. Untuk mengulang eksperimen dengan korpus/model sama, pertahankan snapshot, konfigurasi, dan file indeks.

## Artefak

- `data/snapshots/*.json`: respons API lengkap, wikitext, waktu pengambilan, revision ID/timestamp, dan SHA-256 wikitext.
- `data/source_register.jsonl`: URL sumber, waktu pengambilan, revision ID, hash, dan snapshot.
- `data/articles.jsonl`, `data/chunks_{fixed,section,listing}.jsonl`.
- `artifacts/elias/usage_counts.csv`: jumlah dokumen, butir senarai yang terpakai, dan chunk per strategi.
- `data/indexes/index_manifest.json`: hash korpus, hash setiap indeks, embedder, versi chunker, dan waktu build.
- `data/indexes/`: artefak indeks lokal; `.npy` dan chunk JSON tidak dilacak Git.
- `data/retrieval_cache.jsonl`: cache hasil `Retriever.search`, dikunci oleh hash indeks dan parameter pencarian.
- `data/retrieval_runs.jsonl`: hasil varian eksperimen.

`Retriever` menyediakan `search(...)` dan `index_hash()`. Filter `city` dan `category` diterapkan sebelum pemeringkatan; pada chunk senarai, kategori berasal dari templat (misalnya `eat` atau `see`).

## Definisi ablation

- **A1**: hybrid retrieval pada chunk `fixed`, `section`, dan `listing`.
- **A2**: dense (multilingual E5), BM25, hybrid reciprocal-rank fusion, dan hybrid + cross-encoder reranker.
- **A6**: kebijakan fixed top-k dibanding adaptive; adaptive mulai dari 3 hasil dan memperluas hingga 2× top-k bila skor fusion teratas di bawah ambang konfigurasi (default 0,025).
- **A7**: hasil retrieval yang sama dipotong menjadi dua budget konteks dalam hitungan kata. Ini proksi token yang konsisten tanpa tokenizer model generatif.

Jalankan `uv run python -m unittest discover -s tests` untuk pengujian parser, metadata chunk, filter BM25, cache, dan validasi kueri.
