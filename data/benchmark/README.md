# Benchmark

Folder ini dilacak git karena berisi data kecil yang menentukan reproduksi.

File yang akan diisi:
- `questions_120.jsonl`: 120 pertanyaan dengan label slice.
- `split.json`: pembagian train, dev, test beserta hash.
- `qrels_dev.jsonl`: qrels untuk dev.
- `qrels_test.locked.jsonl`: qrels test yang disegel, dipegang Nad.
- `test_ids.txt`: daftar id test untuk pemeriksaan kebocoran.

Jangan menaruh data mentah atau indeks di sini.
