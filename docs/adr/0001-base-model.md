# ADR 0001: Base generator Qwen2.5-1.5B-Instruct

Status: accepted
Tanggal: 2026-11-21
Pemilik: Ian

## Konteks

Brief mewajibkan base generator yang sama untuk B0 sampai B5. Mesin pengembangan memakai GPU dengan VRAM 6 GB. QLoRA untuk model 7B di VRAM sebesar itu berisiko OOM.

## Keputusan

Pakai `Qwen/Qwen2.5-1.5B-Instruct` untuk B0 sampai B5. Lisensi Apache 2.0. Latihan B5 memakai QLoRA 4-bit, inferensi memakai bfloat16.

## Konsekuensi

- Semua konfigurasi wajib mencatat `model_id` dan `revision` yang sama.
- Runner menolak run kalau `model_id` berbeda.
- Kalau VRAM tidak cukup saat latihan, turunkan sequence length atau pindah ke Colab T4. Jangan mengganti base model di tengah eksperimen.
