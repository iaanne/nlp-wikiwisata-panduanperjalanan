"""Membangun manifest run yang bisa diverifikasi."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

TRACKED_PACKAGES = (
    "torch",
    "transformers",
    "peft",
    "trl",
    "datasets",
    "accelerate",
    "bitsandbytes",
    "sentence-transformers",
    "rank-bm25",
    "jsonschema",
    "pyyaml",
)


def canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_versions() -> dict[str, str]:
    result: dict[str, str] = {}
    for name in TRACKED_PACKAGES:
        try:
            result[name] = version(name)
        except PackageNotFoundError:
            result[name] = "not_installed"
    return result


def git_commit(cwd: str | Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(cwd),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def build_manifest(
    *,
    config: dict[str, Any],
    config_path: str | Path,
    prompt_hashes: dict[str, str],
    index_hash: str | None,
    split: str,
    split_hash: str | None,
    adapter_hash: str | None,
    seed: int,
    dry_run: bool,
    run_id: str | None = None,
    repo_root: str | Path | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    created = created_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    config_id = str(config.get("id", "UNKNOWN"))
    generated_run_id = run_id or (
        f"{config_id}-{split}-{seed}-{created.replace(':', '').replace('-', '')}"
    )

    return {
        "run_id": generated_run_id,
        "created_at": created,
        "config_path": str(config_path),
        "config_hash": sha256_text(canonical_json(config)),
        "git_commit": git_commit(repo_root) if repo_root else None,
        "model": config.get("model", {}),
        "prompt_hashes": prompt_hashes,
        "index_hash": index_hash,
        "split": split,
        "split_hash": split_hash,
        "adapter_hash": adapter_hash,
        "seed": seed,
        "decoding": config.get("decoding", {}),
        "package_versions": package_versions(),
        "hardware": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "gpu": None,
        },
        "dry_run": dry_run,
        "per_item": [],
    }


def write_manifest(manifest: dict[str, Any], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
