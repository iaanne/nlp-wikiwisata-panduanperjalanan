"""Verifikasi bahwa setiap trace log memiliki struktur lengkap dan valid."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRACE = REPO_ROOT / "artifacts" / "jimly" / "sample_logs_and_traces.jsonl"

REQUIRED_TRACE_FIELDS = {
    "request_id",
    "timestamp",
    "source",
    "config_id",
    "question",
    "travel_date",
    "verdict",
    "fallback_used",
    "pii_redacted",
    "prompt_tokens",
    "output_tokens",
    "stages_ms",
    "total_latency_ms",
}


def verify_trace_file(path: Path, expected_request_ids: list[str] | None = None) -> int:
    if not path.exists():
        raise FileNotFoundError(f"File trace tidak ditemukan: {path}")

    seen_ids: set[str] = set()
    count = 0
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        record = json.loads(line)
        missing = REQUIRED_TRACE_FIELDS - set(record.keys())
        if missing:
            raise ValueError(f"{path}:{line_number}: field trace hilang: {sorted(missing)}")
        if record["verdict"] not in {"answered", "abstain"}:
            raise ValueError(f"{path}:{line_number}: verdict tidak valid: {record['verdict']}")
        seen_ids.add(str(record["request_id"]))
        count += 1

    if count == 0:
        raise ValueError(f"File trace kosong: {path}")

    if expected_request_ids:
        missing_ids = [rid for rid in expected_request_ids if rid not in seen_ids]
        if missing_ids:
            raise ValueError(f"request_id tidak ditemukan di trace log: {missing_ids}")

    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verifikasi file trace log serving.")
    parser.add_argument("--trace-log", type=Path, default=DEFAULT_TRACE)
    parser.add_argument("--request-id", action="append", default=[])
    args = parser.parse_args(argv)

    total = verify_trace_file(args.trace_log, args.request_id or None)
    print(f"OK: {total} baris trace terverifikasi di {args.trace_log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
