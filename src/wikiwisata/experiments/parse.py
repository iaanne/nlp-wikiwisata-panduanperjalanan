"""Parsing dan validasi output model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from wikiwisata.experiments.schema import validate


class ParseError(ValueError):
    """Output model bukan JSON yang bisa dibaca."""


def extract_json(raw: str) -> dict[str, Any]:
    text = raw.strip()

    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0].strip()

    start = text.find("{")
    if start == -1:
        raise ParseError("Tidak ada objek JSON di output")

    try:
        data, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError as exc:
        raise ParseError(f"JSON rusak: {exc}") from exc

    if not isinstance(data, dict):
        raise ParseError("JSON harus berupa objek")

    return data


def parse_answer(raw: str, schema_path: str | Path) -> dict[str, Any]:
    data = extract_json(raw)
    validate(data, schema_path)
    return data


def normalize_answer(
    data: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Isi field kosong yang hilang tanpa mengubah isi jawaban."""
    normalized: list[str] = []

    if "answer" not in data and data.get("verdict") == "abstain":
        data["answer"] = ""
        normalized.append("answer")

    for key, default in (
        ("claims", []),
        ("citations", []),
        ("tool_calls", []),
        ("abstain_reason", None),
    ):
        if key not in data:
            data[key] = default
            normalized.append(key)

    if "meta" not in data:
        data["meta"] = {
            "config_id": "",
            "prompt_id": "",
            "prompt_version": "",
        }
        normalized.append("meta")
    elif isinstance(data["meta"], dict):
        for key in ("config_id", "prompt_id", "prompt_version"):
            if key not in data["meta"]:
                data["meta"][key] = ""
                normalized.append(f"meta.{key}")

    claims = data.get("claims")
    if isinstance(claims, list):
        for index, claim in enumerate(claims):
            if isinstance(claim, dict) and "evidence_ids" not in claim:
                claim["evidence_ids"] = []
                normalized.append(f"claims[{index}].evidence_ids")

    return data, normalized


def parse_answer_with_normalization(
    raw: str,
    schema_path: str | Path,
) -> tuple[dict[str, Any], list[str]]:
    data = extract_json(raw)
    data, normalized = normalize_answer(data)
    validate(data, schema_path)
    return data, normalized
