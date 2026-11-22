"""Muat konfigurasi eksperimen dan gabungkan dengan base."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

SPLIT_FILES = {
    "smoke": "smoke_yogyakarta.jsonl",
    "dev": "dev.jsonl",
    "test": "test.jsonl",
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def load_config(path: str | Path) -> dict[str, Any]:
    """Muat YAML dan gabungkan rantai `extends` secara rekursif."""
    config_path = Path(path).resolve()
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config harus berupa mapping: {config_path}")

    parent = data.pop("extends", None)
    if parent is None:
        return data

    parent_path = (config_path.parent / str(parent)).resolve()
    return _deep_merge(load_config(parent_path), data)


def flatten(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Ratifikasi nested dict menjadi kunci bertitik."""
    result: dict[str, Any] = {}
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            result.update(flatten(value, full_key))
        else:
            result[full_key] = value
    return result
