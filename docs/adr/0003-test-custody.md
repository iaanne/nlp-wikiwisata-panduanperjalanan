# ADR 0003: Benchmark dilacak, qrels test disegel

Status: accepted
Tanggal: 2026-11-21
Pemilik: Nad dan Ian

## Konteks

Brief mewajibkan test yang terkunci dan qrels untuk seluruh query. Kalau qrels test disimpan bersama qrels dev dalam satu file, label test bisa terlihat sebelum eksperimen final. Kalau seluruh folder `data/` di-ignore, benchmark tidak ikut git dan hash-nya tidak bisa diverifikasi.

## Keputusan

- `data/benchmark/` dilacak git. Isinya pertanyaan, split, qrels dev, dan qrels test yang disegel.
- `qrels_test.locked.jsonl` hanya dipegang Nad. Hash file dipublikasikan di repo.
- Data mentah, indeks, dan anotasi blind tidak dilacak git.
- Semua run mencatat `split_hash`.

## Konsekuensi

- Orang lain bisa memverifikasi hash test tanpa melihat isinya.
- Setelah test lock, tidak ada perubahan pertanyaan, qrels, prompt, atau indeks.
