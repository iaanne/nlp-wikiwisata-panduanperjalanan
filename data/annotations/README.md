# Anotasi

- `questions_120.jsonl` dan qrels ada di `data/benchmark/`, bukan di sini.
- `blind/` menyimpan anotasi mentah dua annotator dan tidak dilacak git.
- `adjudication_log.jsonl` menyimpan hasil akhir perbedaan label dan dilacak git.

Aturan blind: annotator tidak membuka file annotator lain sebelum kedua file selesai. Merge dilakukan oleh script yang menolak jalan kalau salah satu file belum lengkap.
