# Schema

Schema di folder ini adalah kontrak, bukan dokumentasi bebas.

- `answer.schema.json` dipakai untuk memvalidasi output semua konfigurasi.
- `manifest.schema.json` dipakai untuk memvalidasi manifest run.
- `tool_args/*.schema.json` dipakai untuk memvalidasi argumen tool B6 sebelum tool dijalankan.

Aturan perubahan: ubah schema berarti menaikkan versi dan menjalankan ulang semua konfigurasi yang terdampak. Jangan mengubah schema setelah test lock.
