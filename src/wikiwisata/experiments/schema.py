"""Validasi output dan manifest terhadap JSON Schema."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_schema(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate(instance: Any, schema_path: str | Path) -> None:
    import jsonschema

    schema = load_schema(schema_path)
    jsonschema.validate(instance=instance, schema=schema)
