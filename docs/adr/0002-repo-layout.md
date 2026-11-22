# ADR 0002: Satu pipeline dan package src/wikiwisata

Status: accepted
Tanggal: 2026-11-21
Pemilik: Ian

## Konteks

Rancangan awal memisahkan `pipeline_b1.py`, `pipeline_b4.py`, dan `pipeline_b6.py`. Pemisahan ini membuat logika mudah bercabang, sehingga sulit membuktikan bahwa satu percobaan hanya mengubah satu variabel. Rancangan itu juga menaruh subpackage langsung di bawah `src/`, yang membuat nama seperti `retrieval` berisiko bentrok dan tidak mengikuti src layout standar.

## Keputusan

- Semua konfigurasi memakai satu `pipeline.py` dengan stage yang bisa dimatikan lewat config.
- Stage B4 dan B6 ada di `src/wikiwisata/experiments/stages/`.
- Semua kode ada di dalam package `src/wikiwisata/`.
- Config eksperimen memakai `extends: ../base.yaml`, dan ablation memakai `parent_config` plus `changed`.

## Konsekuensi

- Perbedaan antar konfigurasi bisa diperiksa dengan `scripts/check_config_delta.py`.
- Menambah konfigurasi baru berarti menambah YAML, bukan menyalin pipeline.
- Import memakai bentuk `from wikiwisata.experiments...`.
