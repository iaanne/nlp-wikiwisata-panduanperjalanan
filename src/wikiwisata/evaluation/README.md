# Evaluation

Pemilik: Nad.

File yang direncanakan:
- `metrics.py`: accuracy, citation precision, evidence recall, temporal accuracy, abstain precision dan recall.
- `kappa.py`: Cohen's kappa per slice.
- `stats_tests.py`: rata-rata, simpangan baku, paired bootstrap.
- `error_analysis.py`: kategori kesalahan.

Semua metrik harus bisa dihitung ulang dari qrels dan `artifacts/ian/runs/<run_id>/outputs.jsonl`.
