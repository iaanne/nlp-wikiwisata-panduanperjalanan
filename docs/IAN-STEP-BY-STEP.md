# Bagian Ian: rencana kerja langkah demi langkah

Dokumen ini hanya mengatur bagian Ian pada proyek Wikiwisata. Isinya urutan kerja, berkas yang harus dibuat, perintah, dan kriteria lulus. Bagian Elias, Nad, dan Jimly hanya muncul sebagai antarmuka yang harus disepakati.

Status: draf kerja. Ubah bagian yang ditandai keputusan setelah tim sepakat.

## 0. Batas peran dan antarmuka

| Orang | Yang dipegang | Yang tidak dipegang Ian |
|---|---|---|
| Ian | Runner B0 sampai B6, prompt registry, B1, B4, B5, B6, ablation A3, A4, A5 | Isi korpus dan indeks, qrels dan metrik, UI dan red team |
| Elias | Korpus, chunking, indeks, retriever, A1, A2, A6, A7 | Prompt dan model |
| Nad | Qrels, protokol anotasi, harness evaluasi, 3 run reporting | Prompt dan model |
| Jimly | UI, API, log, trace, guardrail, 20 kasus red team | Prompt dan model |

Tiga antarmuka ini harus disepakati di hari pertama. Tanpa ini, pekerjaan Ian dan Elias akan saling menunggu.

### 0.1 Antarmuka retrieval

Elias menyerahkan satu kelas dan satu cache beku.

```python
class Passage(TypedDict):
    passage_id: str
    doc_id: str
    rev_id: int
    title: str
    section: str
    text: str
    score: float
    rank: int
    lastedit: str | None
    lat: float | None
    lon: float | None

class Retriever:
    index_hash: str
    def search(self, query: str, k: int = 5, filters: dict | None = None) -> list[Passage]:
        ...
```

Aturan:
- Ian tidak membaca berkas indeks langsung. Ian hanya memanggil `search`.
- Elias juga memberi `retrieval_cache.jsonl` berisi hasil retrieval untuk semua query dev dan test. Cache dipakai saat run final supaya hasil bisa diulang tanpa membangun indeks ulang.
- Setiap passage punya `passage_id` stabil. `passage_id` inilah yang muncul di sitasi, bukan nomor urut.
- `index_hash` masuk ke manifest. Kalau hash berubah, run lama tidak boleh dicampur dengan run baru.

### 0.2 Antarmuka output

Semua konfigurasi mengembalikan JSON yang sama. Nad hanya membaca bentuk ini.

```json
{
  "answer": "Teks jawaban akhir.",
  "claims": [
    {
      "claim_id": "c1",
      "text": "Klaim atomik pertama.",
      "status": "supported",
      "evidence_ids": ["p12"]
    }
  ],
  "citations": [
    {
      "passage_id": "p12",
      "doc_id": "Yogyakarta",
      "rev_id": 123456,
      "title": "Yogyakarta",
      "section": "Lihat"
    }
  ],
  "verdict": "answered",
  "abstain_reason": null,
  "tool_calls": [],
  "meta": {
    "config_id": "B4",
    "prompt_id": "b4-answer",
    "prompt_version": "1.0.0"
  }
}
```

Nilai `verdict`: `answered` atau `abstain`. Nilai `status` klaim: `supported`, `unknown`, atau `contradicted`. `abstain_reason` wajib diisi kalau `verdict` sama dengan `abstain`.

Aturan: bentuk ini dibekukan sebelum test lock. Perubahan setelah lock harus lewat versi baru dan dijalankan ulang semua konfigurasi.

### 0.3 Antarmuka manifest

Setiap run menulis satu `manifest.json`. Isi minimum:

| Field | Contoh | Kenapa perlu |
|---|---|---|
| `run_id` | `B4-test-13-20261121T1400` | Identitas run |
| `git_commit` | `a1b2c3d` | Kode yang dipakai |
| `config_hash` | sha256 | Deteksi config berubah |
| `model_id` dan `model_revision` | `Qwen/Qwen2.5-1.5B-Instruct`, commit HF | Model yang dipakai |
| `adapter_hash` | sha256 atau null | LoRA yang dipakai |
| `prompt_ids` dan `prompt_hashes` | daftar | Deteksi prompt berubah |
| `index_hash` | sha256 | Deteksi indeks berubah |
| `retrieval_cache_hash` | sha256 | Deteksi cache berubah |
| `split` dan `split_hash` | `test`, sha256 | Deteksi kebocoran test |
| `seed` | 13 | reproduksi sampling |
| `decoding` | temperature, top_p, max tokens | reproduksi output |
| `package_versions` | transformers, torch, peft | reproduksi environment |
| `hardware` | GPU, VRAM | konteks biaya |
| `per_item` | token masuk, token keluar, latensi | analisis biaya |

## 1. Keputusan yang harus dikunci sebelum koding

| Keputusan | Default yang saya sarankan | Alasan | Cara memastikan |
|---|---|---|---|
| Base generator | `Qwen/Qwen2.5-1.5B-Instruct` | Lisensi Apache 2.0, muat untuk QLoRA di VRAM 6 GB, cukup baik untuk bahasa Indonesia | Cek kartu model di Hugging Face, catat commit revision |
| Model untuk semua B0 sampai B5 | Sama persis | Kewajiban brief | Manifest menolak run kalau `model_id` berbeda |
| Presisi inference | bfloat16 untuk semua konfigurasi | 1.5B muat di 6 GB, dan B5 tidak dibandingkan dengan model terkuantisasi berbeda | Catat `torch_dtype` di manifest |
| Presisi training B5 | 4-bit NF4 QLoRA | Menghemat VRAM | Catat konfigurasi kuantisasi |
| Decoding | temperature 0.2, top_p 0.95, seed 13, 37, 71 | Brief minta 3 run dan varians. Greedy membuat varians nol | Tulis di ADR kalau tim memilih greedy |
| Panjang output | maksimum 512 token baru | Jawaban JSON tetap ringkas | Log jumlah token yang terpotong |
| Tanggal test lock | sepakati di minggu 2 | Setelah lock, tidak ada perubahan prompt dan qrels | Tag git dan hash test set |

Catatan penting: jangan memakai `qwen2.5:7b-instruct-q4_K_M` yang sudah ada di Ollama untuk run terukur. Model itu 7B terkuantisasi, berbeda dari base 1.5B, dan LoRA untuk 7B tidak muat di VRAM 6 GB. Ollama boleh dipakai untuk demo Jimly, bukan untuk angka di laporan.

## Langkah 1: siapkan environment (0.5 hari)

Python bawaan mesin ini 3.14.9, jadi proyek mengunci 3.12 lewat `.python-version`. Jangan memaksa 3.14.

```bash
cd /home/archian/Kuliah/Semester5/NLP/Projek/nlp-wikiwisata-panduanperjalanan
uv sync
```

`uv sync` memasang semua dependensi, termasuk torch. Untuk pemeriksaan ringan tanpa torch:

```bash
uv pip install pyyaml jsonschema pytest
```

Kalau wheel CUDA dari PyPI tidak cocok dengan driver 620, pasang torch dari indeks wheel PyTorch yang sesuai. Jangan mengarang versi.

Jalankan `scripts/check_env.py` yang mencetak versi Python, versi package, `torch.cuda.is_available()`, nama GPU, dan total VRAM. Uji muat tokenizer dan model 1.5B dilakukan terpisah dengan skrip kecil sebelum latihan.

Kriteria lulus:
- `torch.cuda.is_available()` bernilai `True`.
- Model 1.5B termuat tanpa OOM.
- `uv.lock` tersimpan, dan hash file itu masuk catatan setup.

## Langkah 2: scaffold repo dan runner (1 hari)

Struktur lengkap ada di `README.md`. Bagian yang dipegang Ian:

```
configs/
  base.yaml
  experiments/b0_baseline.yaml ... b6_agentic_tool.yaml
  ablations/a3_verifier.yaml a4_adapter.yaml a5_tool_usage.yaml
prompts/
  registry.json
  changelog.md
  system/*.txt
  modules/*.txt
  few_shot/
schemas/
  answer.schema.json
  manifest.schema.json
  tool_args/*.schema.json
src/wikiwisata/
  retrieval/base.py
  experiments/
    harness.py
    pipeline.py
    config.py
    manifest.py
    schema.py
    prompt_manager.py
    generate.py
    parse.py
    train_lora.py
    stages/{planner,verifier,tools}.py
scripts/
  check_tree.py
  check_env.py
  check_config_delta.py
tests/
artifacts/ian/
  runs/
  adapters/
docs/
  IAN-STEP-BY-STEP.md
  adr/
```

Tidak ada `pipeline_b1.py`, `pipeline_b4.py`, atau `pipeline_b6.py`. Semua konfigurasi memakai satu `pipeline.py` dengan stage yang dimatikan lewat config.

Contoh `configs/experiments/b4_planner_verifier.yaml`:

```yaml
id: B4
name: adaptive_rag
extends: ../base.yaml
parent: B3
prompt: b4_answer
prompt_modules:
  - query_planner
  - evidence_check
  - claim_verifier
retrieval:
  enabled: true
  backend: hybrid_rerank
  chunking: fixed
  top_k: 5
  metadata_filter: true
planner:
  enabled: true
verification:
  enabled: true
  max_retries: 1
  max_repair: 1
tools:
  enabled: false
adapter:
  enabled: false
abstain:
  enabled: true
```

Perilaku `python -m wikiwisata.experiments.harness`:
1. Baca config dan gabungkan `extends`.
2. Hitung hash config, prompt, index, dan split.
3. Tolak jalan kalau `model_id` berbeda dari base yang dikunci.
4. Tulis `manifest.json` sebelum inferensi, lalu lengkapi setelah selesai.
5. Simpan output mentah per item ke `artifacts/ian/runs/<run_id>/outputs.jsonl`.
6. Simpan ringkasan token dan latensi ke `artifacts/ian/runs/<run_id>/summary.json`.

Kriteria lulus:
- `python -m wikiwisata.experiments.harness --config configs/experiments/b0_baseline.yaml --dry-run` menghasilkan manifest lengkap tanpa memanggil model.
- Menjalankan dry-run dua kali menghasilkan hash yang sama.
- Mengubah satu karakter di prompt mengubah `prompt_hashes`.
- `check_config_delta.py` mencetak daftar field yang berubah. Kalau lebih dari blok yang dimaksud, runner memberi peringatan.

## Langkah 3: prompt registry (1 hari)

`prompts/registry.json` menyimpan metadata, bukan teks prompt. Teks ada di `prompts/system/` dan `prompts/modules/`.

```json
{
  "schema_version": 1,
  "prompts": [
    {
      "id": "b0_default",
      "version": "1.0.0",
      "file": "system/b0_default_v1.0.txt",
      "sha256": "...",
      "created_at": "2026-11-21",
      "author": "ian",
      "change_note": "versi awal",
      "few_shot": null
    }
  ]
}
```

Aturan:
- Prompt B0: zero-shot, tanpa retrieval, tanpa tool, tanpa verifikasi.
- Prompt B1: few-shot hanya dari train atau dev, ditambah skema output dan aturan abstain.
- Contoh few-shot disimpan di `prompts/few_shot/b1_examples.jsonl` dan setiap baris punya `split: train` atau `split: dev`.
- `python -m wikiwisata.experiments.prompt_manager --check` gagal kalau hash teks tidak cocok dengan registry, atau kalau file prompt tidak ada.
- Mengubah teks prompt berarti versi baru. Jangan menimpa versi lama.

Kriteria lulus:
- `python -m wikiwisata.experiments.prompt_manager --check` lolos.
- Registry memuat hash setiap prompt.
- B1 memakai prompt id dan versi yang sama di semua run B1.

## Langkah 4: B0 dan B1 (2 hari)

B0:
- Satu panggilan model, tanpa konteks dokumen.
- Instruksi hanya meminta jawaban dan format JSON.
- Tidak ada aturan abstain khusus. Kalau model menjawab ngawur, itu temuan, bukan bug yang harus ditambal.

B1:
- Prompt terstruktur berisi definisi field, contoh few-shot dari train, aturan kapan harus `abstain`, dan larangan mengarang sitasi.
- Skema JSON yang sama dengan Bagian 0.2.
- Parser memvalidasi JSON dengan `jsonschema`. Satu kali percobaan perbaikan format boleh, tetapi harus dicatat sebagai `format_repair=true`. Jangan memperbaiki isi jawaban.

Uji asap di 20 item dev:
- parse rate, yaitu persentase output yang valid JSON
- jumlah abstain
- rata-rata token masuk dan keluar
- latensi p50 dan p95
- tiga contoh output yang gagal parse, disimpan untuk analisis

Kriteria lulus:
- Parse rate minimal 98 persen pada B1. Kalau di bawah itu, perbaiki prompt atau parser, bukan menambal output dengan regex yang mengubah isi.
- B0 dan B1 memakai model, presisi, dan decoding yang sama. Yang berbeda hanya prompt.
- Prompt B1 versi 1.2.0 dibekukan setelah uji asap.

## Langkah 5: sambungkan B2 dan B3 (1 sampai 2 hari, setelah Elias siap)

B2:
- Dense retrieval dari Elias, chunk tetap, top-k 5.
- Prompt sama dengan B1. Tidak boleh ada perubahan prompt.
- Output sama dengan B1.

B3:
- Hybrid BM25 plus dense, fusi, reranker, filter metadata.
- Prompt sama dengan B1.
- `top_k` sama dengan B2, supaya perbandingan adil.

Kriteria lulus:
- `git diff configs/experiments/b1_structured_abstain.yaml configs/experiments/b2_retrieval_variant.yaml` hanya menunjukkan blok `retrieval`.
- `git diff configs/experiments/b2_retrieval_variant.yaml configs/experiments/b3_metadata_filtered.yaml` hanya menunjukkan blok `retrieval`.
- Run B2 dan B3 mencatat `index_hash` dan `retrieval_cache_hash` yang sama dengan yang diberikan Elias.
- Semua sitasi di output menunjuk `passage_id` yang benar-benar ada di hasil retrieval.

## Langkah 6: B4 self-corrective (3 hari)

B4 punya empat bagian yang harus terpisah dan bisa dimatikan satu per satu.

1. Query planner.
   - Memecah pertanyaan menjadi sub-pertanyaan.
   - Menentukan apakah sub-pertanyaan butuh retrieval atau bisa dijawab dari konteks sebelumnya.
   - Menggabungkan hasil menjadi satu daftar query retrieval.
2. Evidence sufficiency.
   - Memberi skor cukup atau tidak cukup berdasarkan cakupan passage terhadap sub-pertanyaan.
   - Boleh gabungan aturan sederhana dan penilaian model. Catat komponen mana yang dipakai.
3. Bounded retry.
   - Maksimum satu putaran retrieval tambahan.
   - Kalau masih tidak cukup, keluarkan `abstain`, bukan mengarang.
4. Claim verifier dan bounded repair.
   - Pecah jawaban menjadi klaim atomik.
   - Setiap klaim diberi status dan `evidence_ids`.
   - Klaim tanpa dukungan memicu satu perbaikan. Kalau tetap tidak didukung, klaim dihapus atau jawaban menjadi abstain.

Ablation A3:
- Konfigurasi A3-off: B4 tanpa verifier dan tanpa repair.
- Konfigurasi A3-on: B4 dengan verifier dan satu repair.
- Retrieval, prompt dasar, dan model harus sama. Hanya blok `verification` yang berubah.
- Metrik: persentase klaim tanpa dukungan, false refusal pada pertanyaan answerable, token tambahan, latensi tambahan.

Kriteria lulus:
- Jumlah retry tidak pernah lebih dari satu. Log menunjukkan alasan retry.
- Setiap klaim punya `evidence_ids` atau status `unknown`.
- Tidak ada loop tak berujung. Setiap run punya batas waktu per item.
- Hasil A3-off dan A3-on bisa dibandingkan per item, bukan hanya rata-rata.

## Langkah 7: B5 QLoRA (4 sampai 5 hari)

Data latih:
- 150 sampai 300 contoh dari train split.
- Format: pertanyaan, tanggal perjalanan, passage emas, jawaban JSON lengkap.
- Provenance dicatat: siapa menulis, dari dokumen mana, tanggal, lisensi.
- Tidak boleh ada item test, baik pertanyaan maupun passage jawabannya.
- Kalau sebagian jawaban dihasilkan model besar lalu disaring verifier, tulis di laporan bahwa itu data silver dan jelaskan penyaringnya.

Konfigurasi awal:

| Parameter | Nilai awal |
|---|---|
| Kuantisasi | 4-bit NF4, double quant |
| Compute dtype | bfloat16 |
| LoRA rank | 16 |
| LoRA alpha | 32 |
| LoRA dropout | 0.05 |
| Target module | q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj |
| Learning rate | 2e-4, cosine |
| Warmup | 3 persen |
| Epoch | 2 |
| Max sequence length | 2048 |
| Batch per device | 1 |
| Gradient accumulation | 8 |
| Gradient checkpointing | aktif |

Ini titik awal, bukan resep pasti. Kalau OOM, turunkan max sequence length ke 1024 atau pindahkan latihan ke Colab T4. Jangan mengubah base model.

Latih pada subset kecil dulu, 20 langkah, untuk mengukur VRAM dan waktu per langkah. Baru jalankan penuh setelah angka itu tercatat.

Simpan:
- adapter LoRA
- `training_config.json`
- log loss per langkah
- hash dataset latih
- versi library

Untuk inference B5:
- Muat base yang sama dalam bfloat16.
- Pasang adapter.
- Jalankan pipeline B4 dengan retrieval, prompt, dan budget yang sama.
- Jangan memakai model hasil merge yang berbeda presisi dari B0 sampai B4.

Ablation A4:
- A4-off: B4 tanpa adapter.
- A4-on: B4 dengan adapter.
- Metrik: skor tugas di dev, selisih train dan dev, VRAM puncak, waktu latih, performa di slice OOD. Slice OOD bisa slice konflik atau no-evidence yang tidak dipakai saat latihan.

Kriteria lulus:
- Adapter bisa dimuat di proses baru tanpa error.
- Output B5 benar-benar berbeda dari B4 pada sebagian item. Kalau identik semua, adapter tidak terpasang.
- `adapter_hash` tercatat di manifest.
- Tidak ada penurunan besar di slice no-evidence. Kalau abstain hancur, itu temuan yang harus dilaporkan.

## Langkah 8: B6 guarded agentic (3 hari)

Pilih parent di dev, B4 atau B5, lalu tulis ADR berisi alasan. Jangan memilih parent setelah melihat hasil test.

Tool yang dipakai:
1. `convert_currency(amount, from_currency, to_currency, date)`
   - Memakai tabel kurs beku bertanggal. Jangan mengambil kurs langsung saat evaluasi.
2. `haversine_distance(lat1, lon1, lat2, lon2)`
   - Menghitung jarak lurus antara dua butir.
3. `check_freshness(lastedit, travel_date, max_age_days)`
   - Menentukan apakah data masih segar untuk tanggal perjalanan.
4. `search_places(city, category, keyword)`
   - Mencari butir berdasarkan metadata, bukan teks bebas.

Guardrail:
- Argumen divalidasi dengan JSON Schema sebelum tool dijalankan.
- Tool bersifat read-only. Tidak ada operasi tulis, hapus, atau kirim.
- Maksimum 4 panggilan tool per item.
- Timeout 5 detik per panggilan.
- Hasil tool dikembalikan ke model sebagai observasi, bukan langsung dijadikan jawaban.
- Jawaban akhir tetap melewati verifier B4.
- Setiap panggilan dicatat: nama tool, argumen, hasil, status validasi, durasi.

Ablation A5:
- A5-off: B6 tanpa tool, konfigurasi lain sama.
- A5-on: B6 dengan tool.
- Metrik: tool correctness, unsafe call rate, budget overrun, end-task outcome.
- Tool correctness dinilai otomatis untuk tool deterministik. Contoh: hasil konversi mata uang dicocokkan dengan tabel kurs.

Kriteria lulus:
- Argumen tidak valid ditolak, dan model menerima pesan error yang bisa dibaca.
- Tidak ada item yang melebihi 4 panggilan.
- Semua tool call punya log lengkap.
- B6 dibandingkan dengan parent yang sama, bukan dengan B0.

## Langkah 9: run matrix, 3 run, dan test lock (3 hari)

Matriks:
- B0 sampai B6, masing-masing 3 run.
- Total 21 run.
- Dev dipakai untuk memilih konfigurasi dan parent B6.
- Test dipakai sekali setelah lock. Setelah lock, tidak ada perubahan prompt, qrels, indeks, atau config.

Aturan run:
- Seed berbeda: 13, 37, 71.
- Retrieval memakai cache beku yang sama untuk semua run.
- Output mentah disimpan per item.
- Item yang gagal karena timeout tetap dihitung, jangan dibuang.
- Jangan memilih run terbaik. Laporkan rata-rata, simpangan baku, dan interval kepercayaan.

Analisis:
- Bandingkan per slice: mudah, multi-hop, temporal atau konflik, no-evidence.
- Uji signifikansi dengan paired bootstrap per item. Jangan menyimpulkan peningkatan hanya dari selisih rata-rata.
- Laporkan biaya per kualitas: token dan latensi terhadap skor.

Kriteria lulus:
- 21 manifest lengkap dan bisa dicocokkan dengan output mentah.
- Angka di tabel ringkasan bisa dihitung ulang dari `outputs.jsonl`.
- Test set hash sama di semua run.
- Tidak ada prompt atau config yang berubah setelah tanggal lock.

## Langkah 10: serah terima dan laporan (2 hari)

Ke Nad:
- Skema output final.
- Daftar `run_id`.
- Contoh 50 item untuk anotasi klaim pada A3.
- Catatan kegagalan parse dan timeout.

Ke Jimly:
- Fungsi `predict(question, travel_date, config_id)`.
- Path adapter B5.
- Batas waktu dan fallback saat model gagal.
- Contoh request dan response.

Ke laporan:
- Tabel konfigurasi B0 sampai B6.
- Tabel ablation A3, A4, A5.
- Grafik biaya per kualitas.
- ADR: pemilihan base model, pemilihan parent B6, perubahan prompt.
- Analisis kesalahan dengan kategori: retrieval salah, reasoning salah, sitasi salah, format gagal, abstain salah.

Kriteria lulus:
- Orang lain bisa menjalankan satu konfigurasi dari README tanpa bertanya.
- Setiap angka di laporan punya `run_id` asal.
- Setiap keputusan desain punya ADR atau catatan perubahan prompt.

## Urutan waktu 10 hari kerja

| Hari | Pekerjaan | Hasil yang dicek |
|---|---|---|
| 1 | Environment dan scaffold | GPU terdeteksi, model 1.5B termuat, dry-run manifest jalan |
| 2 | Prompt registry dan B0 | B0 jalan di 20 dev, manifest lengkap |
| 3 | B1 dan uji asap | Parse rate minimal 98 persen, prompt v1 dibekukan |
| 4 | B2 dan B3 | Config diff hanya blok retrieval, sitasi valid |
| 5 | B4 planner dan retry | Retry maksimum satu, abstain jalan |
| 6 | B4 verifier dan A3 | Klaim punya bukti, A3-off dan A3-on bisa dibandingkan |
| 7 | Data latih B5 | 150 contoh, provenance lengkap, tidak ada test |
| 8 | Latih dan uji B5 | Adapter termuat, VRAM dan waktu tercatat |
| 9 | B6 dan A5 | Tool tervalidasi, budget tidak terlampaui |
| 10 | Run matrix dan serah terima | 21 manifest, ringkasan, handoff ke Nad dan Jimly |

Kalau Elias terlambat, hari 4 dan 5 bisa digeser. Jangan mengarang indeks sementara yang berbeda dari indeks final, karena angka B2 dan B3 tidak akan bisa dibandingkan.

## Definition of done bagian Ian

- [ ] Base model dikunci dan sama di B0 sampai B5.
- [ ] Runner menghasilkan manifest lengkap untuk setiap run.
- [ ] Prompt registry punya hash dan catatan perubahan.
- [ ] B0, B1, B2, B3, B4, B5, B6 semuanya bisa dijalankan dengan satu perintah.
- [ ] A3, A4, A5 masing-masing hanya mengubah satu variabel.
- [ ] 3 run per konfigurasi di test subset.
- [ ] Output mentah, token, dan latensi tersimpan.
- [ ] Adapter dan training log tersimpan.
- [ ] Parent B6 dipilih di dev dan punya ADR.
- [ ] Handoff ke Nad dan Jimly selesai.
- [ ] Tidak ada item test yang bocor ke prompt, few-shot, atau data latih.

## Risiko yang harus dipantau

| Risiko | Tanda | Tindakan |
|---|---|---|
| VRAM 6 GB tidak cukup | OOM saat latihan | Turunkan sequence length, gradient checkpointing, atau pindah ke Colab T4 |
| Python 3.14 tidak didukung | Instalasi torch gagal | Pakai venv Python 3.12 lewat uv |
| Model 7B Ollama tercampur | Angka B0 berbeda dari B5 | Kunci `model_id` di manifest, tolak run yang beda |
| Format JSON sering gagal | Parse rate di bawah 98 persen | Perbaiki prompt dan schema, jangan menambal isi dengan regex |
| Prompt berubah di tengah jalan | Hash prompt beda antar run | Registry versi, runner menolak hash tak dikenal |
| Indeks berubah | `index_hash` beda | Cache retrieval beku, run baru dengan nama baru |
| Test bocor | Few-shot atau data latih memuat item test | `check_prompts.py` dan hash split |
| LoRA overfit | Skor train naik, dev turun | Kurangi epoch, tambah dropout, evaluasi slice OOD |
| Tool tidak deterministik | Hasil kurs berubah antar run | Tabel kurs beku bertanggal |
| 3 run identik | Varians nol | Catat sebagai determinisme, atau pakai temperature 0.2 |

## Keputusan yang perlu dibicarakan dengan tim

1. Base model 1.5B atau 3B. 3B kemungkinan butuh Colab untuk QLoRA, jadi keputusan ini menentukan jadwal.
2. Siapa menulis 150 sampai 300 data latih B5. Ini pekerjaan terbesar yang sering diremehkan.
3. Tanggal test lock.
4. Temperature 0.2 atau greedy. Brief minta varians, greedy memberi varians nol.
5. Apakah B6 memakai parent B4 atau B5. Diputuskan di dev, bukan di test.

## Istilah

| Istilah | Arti singkat |
|---|---|
| manifest | Berkas catatan identitas dan konfigurasi satu run |
| run | Satu eksekusi lengkap semua item pada satu konfigurasi |
| qrels | Label relevansi passage untuk setiap query |
| split | Pembagian data menjadi train, dev, dan test |
| lock | Membekukan test set dan konfigurasi sebelum evaluasi final |
| QLoRA | LoRA yang dilatih di atas model terkuantisasi 4-bit |
| adapter | Bobot kecil hasil fine-tuning yang dipasang ke base model |
| LoRA | Fine-tuning parameter efisien dengan matriks rank rendah |
| retry | Percobaan retrieval ulang setelah bukti dinilai kurang |
| verifier | Komponen yang memeriksa klaim terhadap passage |
| abstain | Sistem menyatakan tidak punya bukti yang cukup |
| OOD | Data di luar distribusi latihan |
| paired bootstrap | Uji ulang sampel berpasangan untuk selang kepercayaan |
| ADR | Catatan keputusan arsitektur beserta alasannya |
