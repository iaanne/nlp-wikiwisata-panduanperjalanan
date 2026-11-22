# Wikiwisata

Asisten rencana perjalanan berbasis RAG dengan tujuh konfigurasi pembanding B0 sampai B6.

Status: B0/B1 sudah jalan end-to-end di smoke set. B2-B6, retrieval, evaluasi, dan serving belum diimplementasikan.

## Peta pemilik

| Area | Pemilik | Lokasi |
|---|---|---|
| Eksperimen B0-B6, prompt, LoRA, ablation A3-A5 | Ian | `src/wikiwisata/experiments/`, `configs/experiments/`, `configs/ablations/a3-a5` |
| Korpus, chunking, indeks, retrieval, A1, A2, A6, A7 | Elias | `src/wikiwisata/corpus/`, `src/wikiwisata/retrieval/`, `configs/ablations/a1, a2, a6, a7` |
| Qrels, anotasi, metrik, 3 run | Nad | `src/wikiwisata/evaluation/`, `data/benchmark/`, `data/annotations/` |
| UI, API, log, red team | Jimly | `src/wikiwisata/serving/`, `configs/serving/`, `data/red_team/` |

## Struktur

```text
configs/
  base.yaml
  experiments/b0_baseline.yaml ... b6_agentic_tool.yaml
  ablations/a1_chunking.yaml ... a7_context_budget.yaml
  serving/{api,red_team}.yaml

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
  corpus/
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
  evaluation/
  serving/

tests/
data/
  benchmark/        dilacak git
  registry/         dilacak git
  training/         dilacak git
  tool_fixtures/    dilacak git
  red_team/         dilacak git
  annotations/      anotasi blind tidak dilacak
  raw/              tidak dilacak
  processed/        tidak dilacak
  indexes/          tidak dilacak, kecuali index_manifest.json

artifacts/
  elias/ ian/ nad/ jimly/

docs/
  IAN-STEP-BY-STEP.md
  adr/
  ATTRIBUTION.md
```

## Setup

Environment penuh, termasuk torch:

```bash
uv sync
```

Environment ringan untuk memeriksa struktur dan kontrak, tanpa mengunduh torch:

```bash
uv venv --python 3.12 .venv
uv pip install pyyaml jsonschema pytest
```

## Perintah

```bash
make tree
make smoke
make check
```

- `make tree` memeriksa kelengkapan struktur.
- `make smoke` menjalankan dry-run B0 dan menulis manifest ke `artifacts/ian/runs/`.
- `make check` menjalankan tes kontrak.

Dry-run manual:

```bash
PYTHONPATH=src .venv/bin/python -m wikiwisata.experiments.harness \
  --config configs/experiments/b4_planner_verifier.yaml \
  --dry-run --output-dir /tmp/wikiwisata-run
```

Bandingkan dua config:

```bash
PYTHONPATH=src .venv/bin/python scripts/check_config_delta.py \
  configs/experiments/b3_metadata_filtered.yaml \
  configs/experiments/b4_planner_verifier.yaml
```

## Aturan

- Base generator dikunci di `configs/base.yaml` dan sama untuk B0 sampai B5.
- Satu ablation hanya mengubah satu kunci. Tes `test_configs.py` menjaga aturan ini.
- `data/benchmark/` dilacak git. Qrels test disegel dan hanya dipegang Nad, hash-nya dipublikasikan.
- Data mentah, indeks, bobot adapter, dan output mentah tidak masuk git.
- Setelah test lock, tidak ada perubahan prompt, qrels, atau indeks.

## Dokumen

- [Rencana kerja Ian](docs/IAN-STEP-BY-STEP.md)
- [ADR base model](docs/adr/0001-base-model.md)
- [ADR struktur repo](docs/adr/0002-repo-layout.md)
- [ADR test custody](docs/adr/0003-test-custody.md)
- [Atribusi korpus](docs/ATTRIBUTION.md)

## Hasil smoke terakhir

| Config | Run | Parse rate | Strict parse | Abstain | Supported tanpa bukti |
|---|---|---|---|---|---|
| B0 | `B0-smoke-13-20261122T062437Z` | 53,3% | 26,7% | 2 | 6 |
| B1 | `B1-smoke-13-20261122T062618Z` | 53,3% | 53,3% | 0 | 8 |

Angka ini diagnostik, bukan hasil final. B1 belum memenuhi aturan abstain dan masih menghasilkan klaim `supported` tanpa bukti.

## Status yang belum selesai

- `pipeline.run` baru mendukung B0/B1. B2 sampai B6 masih stub.
- `prompts/few_shot/b1_examples.jsonl` belum diisi.
- `data/benchmark/` baru berisi 15 pertanyaan smoke. Dev, test, dan qrels belum ada.
- `data/indexes/index_manifest.json` masih `not_built`.
- `artifacts/ian/adapters/` belum berisi adapter B5.
