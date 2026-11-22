"""Runner skeleton untuk B0 sampai B6."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from wikiwisata.experiments.config import SPLIT_FILES, load_config
from wikiwisata.experiments.manifest import (
    build_manifest,
    sha256_file,
    write_manifest,
)
from wikiwisata.experiments.prompt_manager import prompt_hashes, verify_hashes

REPO_ROOT = Path(__file__).resolve().parents[3]


def _read_hash(path: Path, key: str) -> str | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    value = data.get(key)
    return str(value) if value else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Jalankan satu konfigurasi Wikiwisata."
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--split", default="dev")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)

    config = load_config(args.config)
    seed = args.seed if args.seed is not None else int(config.get("seed", 13))

    prompts_dir = REPO_ROOT / "prompts"
    verify_hashes(prompts_dir)

    prompt_ids = list(
        dict.fromkeys(
            [config["prompt"], *config.get("prompt_modules", [])]
        )
    )
    hashes = prompt_hashes(prompts_dir, prompt_ids)

    index_manifest = REPO_ROOT / "data/indexes/index_manifest.json"
    split_file = SPLIT_FILES.get(args.split)
    if split_file is None:
        parser.error(f"Split tidak dikenal: {args.split}")
    split_path = REPO_ROOT / "data/benchmark" / split_file
    if not split_path.exists():
        parser.error(f"Dataset split tidak ada: {split_path}")
    adapter_path = Path(
        config.get("adapter", {}).get("path", "artifacts/ian/adapters/b5")
    )
    adapter_manifest = REPO_ROOT / adapter_path / "adapter_manifest.json"

    try:
        config_label = str(Path(args.config).resolve().relative_to(REPO_ROOT))
    except ValueError:
        config_label = str(Path(args.config).resolve())

    manifest = build_manifest(
        config=config,
        config_path=config_label,
        prompt_hashes=hashes,
        index_hash=_read_hash(index_manifest, "index_hash"),
        split=args.split,
        split_hash=sha256_file(split_path),
        adapter_hash=_read_hash(adapter_manifest, "adapter_hash"),
        seed=seed,
        dry_run=args.dry_run,
        repo_root=REPO_ROOT,
    )

    output_dir = args.output_dir or (REPO_ROOT / "artifacts/ian/runs")
    run_dir = output_dir / manifest["run_id"]
    run_dir.mkdir(parents=True, exist_ok=True)
    write_manifest(manifest, run_dir / "manifest.json")
    (run_dir / "config.resolved.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    print(run_dir / "manifest.json")

    if args.dry_run:
        return 0

    from wikiwisata.experiments.pipeline import run

    result = run(config, split=args.split, seed=seed)

    with (run_dir / "outputs.jsonl").open("w", encoding="utf-8") as handle:
        for item in result["items"]:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    (run_dir / "summary.json").write_text(
        json.dumps(result["summary"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    manifest["per_item"] = [
        {
            "id": item["id"],
            "slice": item["slice"],
            "prompt_tokens": item["prompt_tokens"],
            "output_tokens": item["output_tokens"],
            "latency_ms": item["latency_ms"],
            "parse_ok": item["parse_error"] is None,
            "verdict": (item["output"] or {}).get("verdict"),
        }
        for item in result["items"]
    ]
    manifest["summary"] = result["summary"]
    write_manifest(manifest, run_dir / "manifest.json")

    print(json.dumps(result["summary"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
