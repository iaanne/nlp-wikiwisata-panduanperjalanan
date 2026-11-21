"""Parsing dan validasi output model."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def parse_answer(raw: str, schema_path: str | Path) -> dict[str, Any]:
    raise NotImplementedError("Implementasi parse ada di langkah 4.")
