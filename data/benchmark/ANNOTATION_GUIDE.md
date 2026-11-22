# Panduan anotasi benchmark Wikiwisata

## Unit dan urutan kerja

Setiap pertanyaan final memiliki `id`, `split`, `slice`, `question`, `travel_date`, dan `answerable`. Target kerja sekarang adalah 150 pertanyaan unik. Berkas `questions_150.draft.jsonl` belum memenuhi komposisi slice yang seimbang; label dan status answerable di dalamnya masih usulan. Tulis pertanyaan dari snapshot korpus, bukan dari keluaran model. Pisahkan dev dan test berdasarkan `page_id` sebelum melihat hasil model.

Kunci korpus adalah pasangan `doc_id`/`revision_id`; kunci passage adalah `chunk_id` dari strategi chunking yang dibekukan. B2/B3 memakai chunk `fixed`, sehingga qrels dev untuk keduanya harus memakai ID `fixed`. Kandidat `listing` dalam `qrels_150_candidates.draft.jsonl` tidak boleh langsung dipakai untuk metrik B2/B3. Untuk ablation A1, petakan gold unit ke ketiga strategi secara terpisah. Simpan `corpus_hash`, `index_hash`, dan strategi chunking bersama anotasi. Perubahan indeks membatalkan qrels lama sampai ID passage dipetakan dan diperiksa ulang.

1. Nad menyusun pertanyaan dan panduan ini; Elias memeriksa apakah pertanyaan sesuai snapshot tanpa melihat jawaban model.
2. Nad dan Elias menilai passage secara terpisah pada daftar kandidat yang sama. File blind masing-masing tidak boleh dibuka oleh annotator lain sebelum keduanya selesai.
3. Hitung Cohen's kappa per slice dari seluruh pasangan `(question_id, chunk_id)` yang sama, termasuk label 0. Jangan hanya menghitung passage relevan.
4. Catat setiap perbedaan dalam `adjudication_log.jsonl`, lalu putuskan label akhir bersama Ian. Qrels final baru dibuat setelah adjudikasi.

## Label passage

| Label | Arti |
|---|---|
| 0 | Tidak relevan, salah tempat/tanggal/revisi, atau hanya menyebut topik tanpa mendukung jawaban. |
| 1 | Mendukung sebagian jawaban atau memberi konteks yang berguna, tetapi tidak cukup untuk membuktikan semua klaim yang diminta. |
| 2 | Passage wajib: memuat fakta yang diperlukan untuk jawaban yang benar; tanpa passage ini atau padanannya, jawaban tidak dapat dibuktikan. |

Untuk multi-hop, beri 2 pada tiap passage yang menyediakan satu mata rantai yang tidak tergantikan. Catat kelompok passage alternatif bila dua sumber sama-sama membuktikan fakta yang sama; keduanya jangan dihitung sebagai dua kewajiban terpisah. Jika tanggal perjalanan meminta keadaan pada waktu tertentu, revisi di luar periode itu bernilai 0 meskipun menyebut fakta yang sama. `answerable=false` hanya bila seluruh snapshot yang boleh dipakai tidak cukup; tulis alasan dan apa bukti yang kurang. Jangan menganggap hasil pencarian top-k yang kosong sebagai bukti bahwa korpus tidak punya jawaban.

## Kasus batas

- Passage menyebut nama tempat tetapi tidak menjawab jam buka yang ditanya: 0.
- Passage memberi alamat, sedangkan pertanyaan meminta alamat dan harga: 1; passage harga yang diperlukan mendapat 2.
- Dua revisi bertentangan: revisi yang cocok dengan `travel_date` dapat mendapat 2, revisi lain 0. Jika tanggal efektif perubahan tak diketahui, tandai untuk adjudikasi; jangan menebak.
- Pertanyaan meminta nomor kontak pribadi: tandai sebagai kasus privasi terpisah. Keberadaan nomor di korpus tidak otomatis mengizinkan sistem menampilkannya.

## Format dan pemeriksaan

Satu baris JSON per pasangan pertanyaan–passage dalam file blind dan qrels final:

```json
{"question_id":"q001","chunk_id":"<ID dari indeks>","relevance":2,"annotator":"nad","reason":"Fakta yang membuktikan jawaban","corpus_hash":"<hash>"}
```

Untuk pertanyaan tanpa bukti, tulis satu baris terpisah di file keputusan pertanyaan dengan `question_id`, `answerable:false`, `abstain_reason`, dan lingkup korpus yang diperiksa. Sebelum metrik dihitung, periksa 150 ID unik, komposisi slice, ID chunk yang benar-benar ada, hash yang sama, kedua file blind lengkap, log perbedaan, dan qrels final hasil adjudikasi.

`split.draft.json` dan `questions_dev.draft.jsonl` adalah split sementara 25 dev dan 125 test. `annotation_packet_dev.draft.jsonl` berisi kandidat chunk fixed tanpa label (`relevance:null`), termasuk passage pengalih untuk menilai label 0. Nad dan Elias masing-masing menyalin paket yang sama ke file blind pribadi dan mengisi label secara terpisah. Jangan bagikan `draft_answer` saat anotasi. Jangan mengganti nama file draf menjadi `qrels_dev.jsonl` sebelum kedua anotator selesai, kappa dihitung, perbedaan diadjudikasi, dan pertanyaan dibekukan.
