"""Registry prompt dan pemeriksaan hash."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from wikiwisata.experiments.manifest import sha256_file


def load_registry(prompts_dir: str | Path) -> dict[str, Any]:
    path = Path(prompts_dir) / "registry.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("schema_version registry tidak dikenal")
    return data


def _entries(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entry["id"]: entry for entry in registry["prompts"]}


def get_entry(prompts_dir: str | Path, prompt_id: str) -> dict[str, Any]:
    registry = load_registry(prompts_dir)
    return _entries(registry)[prompt_id]


def verify_hashes(
    prompts_dir: str | Path,
    registry: dict[str, Any] | None = None,
) -> None:
    base = Path(prompts_dir)
    registry = registry or load_registry(base)
    errors: list[str] = []
    for entry in registry["prompts"]:
        path = base / entry["file"]
        if not path.exists():
            errors.append(f"{entry['id']}: file tidak ada ({path})")
            continue
        actual = sha256_file(path)
        if actual != entry["sha256"]:
            errors.append(
                f"{entry['id']}: hash beda ({actual} != {entry['sha256']})"
            )
    if errors:
        raise ValueError("\n".join(errors))


def prompt_hashes(
    prompts_dir: str | Path,
    prompt_ids: list[str],
) -> dict[str, str]:
    base = Path(prompts_dir)
    registry = load_registry(base)
    by_id = _entries(registry)
    result: dict[str, str] = {}
    for prompt_id in prompt_ids:
        if prompt_id not in by_id:
            raise KeyError(f"Prompt tidak ada di registry: {prompt_id}")
        result[prompt_id] = by_id[prompt_id]["sha256"]
    return result


def read_prompt(prompts_dir: str | Path, prompt_id: str) -> str:
    base = Path(prompts_dir)
    registry = load_registry(base)
    entry = _entries(registry)[prompt_id]
    return (base / entry["file"]).read_text(encoding="utf-8")


def check_few_shot_leakage(
    prompts_dir: str | Path,
    test_ids: set[str],
) -> list[str]:
    base = Path(prompts_dir)
    registry = load_registry(base)
    problems: list[str] = []
    for entry in registry["prompts"]:
        few_shot = entry.get("few_shot")
        if not few_shot:
            continue
        path = base / few_shot
        if not path.exists():
            problems.append(f"{entry['id']}: file few-shot tidak ada ({path})")
            continue
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if not line.strip():
                continue
            item = json.loads(line)
            example_id = str(item.get("example_id", ""))
            split = item.get("split")
            if split not in {"train", "dev"}:
                problems.append(
                    f"{path}:{line_number}: split harus train atau dev, bukan {split}"
                )
            if example_id in test_ids:
                problems.append(
                    f"{path}:{line_number}: example_id {example_id} ada di test"
                )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Periksa registry prompt.")
    parser.add_argument("--prompts-dir", default="prompts")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        verify_hashes(args.prompts_dir)
        print("Prompt registry OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
