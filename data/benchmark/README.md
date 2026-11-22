# Benchmark

Folder ini dilacak git karena berisi data kecil yang menentukan reproduksi.

File kerja saat ini:
- `questions_150.draft.jsonl`: 150 pertanyaan usulan; slice dan answerable belum divalidasi.
- `split.draft.json`: pembagian sementara 25 dev dan 125 test berdasarkan artikel, beserta SHA-256 file pertanyaan.
- `questions_dev.draft.jsonl`: 25 pertanyaan dev sementara.
- `annotation_packet_dev.draft.jsonl`: kandidat passage `fixed` untuk dua annotator, tanpa label relevansi.
- `qrels_150_candidates.draft.jsonl`: kandidat berbasis `listing`, **bukan qrels final untuk B2/B3**.

File setelah review dan anotasi blind:
- `split.json`: pembagian final dev/test beserta hash.
- `qrels_dev.jsonl`: qrels dev hasil adjudikasi.
- `qrels_test.locked.jsonl`: qrels test yang disegel, dipegang Nad dan tidak di-commit.
- `test_ids.txt`: daftar id test untuk pemeriksaan kebocoran.

Jangan menaruh data mentah atau indeks di sini.
