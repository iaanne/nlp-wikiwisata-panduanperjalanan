"""Pipeline tunggal untuk B0 sampai B6.

Stage dimatikan lewat config, bukan lewat file pipeline terpisah.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from wikiwisata.experiments.config import SPLIT_FILES
from wikiwisata.experiments.generate import generate
from wikiwisata.experiments.parse import parse_answer_with_normalization
from wikiwisata.experiments.prompt_manager import get_entry, read_prompt

REPO_ROOT = Path(__file__).resolve().parents[3]
PROMPTS_DIR = REPO_ROOT / "prompts"
SCHEMA_PATH = REPO_ROOT / "schemas/answer.schema.json"
BENCHMARK_DIR = REPO_ROOT / "data/benchmark"


def fill_template(template: str, values: dict[str, Any]) -> str:
    """Ganti placeholder tanpa menyentuh kurung kurawal JSON."""
    result = template
    for key, value in values.items():
        result = result.replace("{" + key + "}", str(value))
    return result


def load_split(split: str) -> list[dict[str, Any]]:
    filename = SPLIT_FILES.get(split)
    if filename is None:
        raise ValueError(f"Split tidak dikenal: {split}")

    path = BENCHMARK_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Dataset split tidak ada: {path}")

    items: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: JSONL rusak: {exc}") from exc

    if not items:
        raise ValueError(f"Dataset split kosong: {path}")
    return items


def _passages_text(config: dict[str, Any]) -> str:
    if not config.get("retrieval", {}).get("enabled"):
        return "(tidak ada passage)"
    return "(retrieval belum diimplementasikan pada pipeline ini)"


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))
    return ordered[index]


def summarize(
    results: list[dict[str, Any]],
    config_id: str,
    split: str,
    seed: int,
) -> dict[str, Any]:
    total = len(results)
    parsed = [result for result in results if result["parse_error"] is None]
    strict = [result for result in parsed if not result.get("normalized")]
    abstain = [
        result
        for result in results
        if (result["output"] or {}).get("verdict") == "abstain"
    ]
    answered = [
        result
        for result in results
        if (result["output"] or {}).get("verdict") == "answered"
    ]
    answerable = [result for result in results if result["answerable"] is True]
    unanswerable = [result for result in results if result["answerable"] is False]
    supported_without_evidence = sum(
        1
        for result in results
        if result["output"]
        for claim in result["output"].get("claims", [])
        if claim.get("status") == "supported" and not claim.get("evidence_ids")
    )

    return {
        "config_id": config_id,
        "split": split,
        "seed": seed,
        "items": total,
        "parsed": len(parsed),
        "parse_failures": total - len(parsed),
        "parse_rate": round(len(parsed) / total, 4) if total else 0.0,
        "strict_parsed": len(strict),
        "strict_parse_rate": round(len(strict) / total, 4) if total else 0.0,
        "normalized_items": len(parsed) - len(strict),
        "answered": len(answered),
        "abstain": len(abstain),
        "abstain_on_answerable": sum(
            1
            for result in answerable
            if (result["output"] or {}).get("verdict") == "abstain"
        ),
        "abstain_on_unanswerable": sum(
            1
            for result in unanswerable
            if (result["output"] or {}).get("verdict") == "abstain"
        ),
        "supported_without_evidence": supported_without_evidence,
        "format_repairs": sum(
            1 for result in results if result.get("format_repair")
        ),
        "repair_successes": sum(
            1
            for result in results
            if result.get("format_repair") and result["parse_error"] is None
        ),
        "total_repair_prompt_tokens": sum(
            result.get("repair_prompt_tokens", 0) for result in results
        ),
        "total_repair_output_tokens": sum(
            result.get("repair_output_tokens", 0) for result in results
        ),
        "total_prompt_tokens": sum(result["prompt_tokens"] for result in results),
        "total_output_tokens": sum(result["output_tokens"] for result in results),
        "mean_latency_ms": (
            round(sum(result["latency_ms"] for result in results) / total, 1)
            if total
            else 0.0
        ),
        "p95_latency_ms": _p95([result["latency_ms"] for result in results]),
    }


def run(
    config: dict[str, Any],
    split: str = "dev",
    seed: int | None = None,
) -> dict[str, Any]:
    items = load_split(split)
    prompt_id = str(config["prompt"])
    template = read_prompt(PROMPTS_DIR, prompt_id)
    entry = get_entry(PROMPTS_DIR, prompt_id)
    repair_template = read_prompt(PROMPTS_DIR, "format_repair")
    config_id = str(config.get("id", "UNKNOWN"))
    seed_value = int(seed if seed is not None else config.get("seed", 13))

    results: list[dict[str, Any]] = []
    for item in items:
        prompt = fill_template(
            template,
            {
                "question": item.get("question", ""),
                "travel_date": item.get("travel_date", ""),
                "passages": _passages_text(config),
            },
        )
        generation = generate(prompt, config, seed=seed_value)

        parsed = None
        parse_error = None
        normalized: list[str] = []
        format_repair = False
        repair_raw_output = None
        repair_prompt_tokens = 0
        repair_output_tokens = 0
        repair_latency_ms = 0.0

        try:
            parsed, normalized = parse_answer_with_normalization(
                generation.text, SCHEMA_PATH
            )
            parsed["meta"]["config_id"] = config_id
            parsed["meta"]["prompt_id"] = prompt_id
            parsed["meta"]["prompt_version"] = entry["version"]
        except Exception as exc:
            parse_error = f"{type(exc).__name__}: {exc}"

        if parse_error is not None:
            format_repair = True
            repair_prompt = fill_template(
                repair_template,
                {"error": parse_error, "raw_output": generation.text},
            )
            repaired = generate(repair_prompt, config, seed=seed_value)
            repair_raw_output = repaired.text
            repair_prompt_tokens = repaired.prompt_tokens
            repair_output_tokens = repaired.output_tokens
            repair_latency_ms = repaired.latency_ms
            try:
                parsed, normalized = parse_answer_with_normalization(
                    repaired.text, SCHEMA_PATH
                )
                parsed["meta"]["config_id"] = config_id
                parsed["meta"]["prompt_id"] = prompt_id
                parsed["meta"]["prompt_version"] = entry["version"]
                parse_error = None
            except Exception as exc:
                parse_error = (
                    f"{parse_error} | repair: {type(exc).__name__}: {exc}"
                )

        results.append(
            {
                "id": item.get("id"),
                "slice": item.get("slice"),
                "answerable": item.get("answerable"),
                "question": item.get("question"),
                "travel_date": item.get("travel_date"),
                "config_id": config_id,
                "prompt_id": prompt_id,
                "prompt_version": entry["version"],
                "raw_output": generation.text,
                "output": parsed,
                "parse_error": parse_error,
                "normalized": normalized,
                "format_repair": format_repair,
                "repair_raw_output": repair_raw_output,
                "repair_prompt_tokens": repair_prompt_tokens,
                "repair_output_tokens": repair_output_tokens,
                "repair_latency_ms": repair_latency_ms,
                "prompt_tokens": generation.prompt_tokens,
                "output_tokens": generation.output_tokens,
                "latency_ms": generation.latency_ms,
                "seed": seed_value,
            }
        )

    return {
        "items": results,
        "summary": summarize(results, config_id, split, seed_value),
    }
