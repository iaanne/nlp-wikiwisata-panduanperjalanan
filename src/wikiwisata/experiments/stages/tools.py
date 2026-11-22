"""Registry dan pemanggilan tool B6."""

from __future__ import annotations

from typing import Any


def call_tool(
    name: str,
    arguments: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    raise NotImplementedError("Implementasi tool ada di langkah 8.")
