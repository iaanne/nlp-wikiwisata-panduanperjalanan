# Bukti Ian

- `runs/<run_id>/manifest.json`: identitas run.
- `runs/<run_id>/config.resolved.yaml`: config setelah merge.
- `runs/<run_id>/outputs.jsonl`: output mentah, tidak dilacak git.
- `runs/<run_id>/summary.json`: token dan latensi.
- `adapters/b5/`: adapter LoRA, config, dan training log.
- `config_table_b0_b6.md`: tabel konfigurasi.
- `parent_decision_b6.md`: ADR pemilihan parent B6.

Bobot adapter dan output mentah tidak masuk git. Yang dilacak adalah manifest, summary, dan SHA-256.
