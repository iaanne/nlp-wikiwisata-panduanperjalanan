"""Pencatat trace dan log per request untuk modul serving Wikiwisata."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TRACE_LOG_PATH = REPO_ROOT / "artifacts" / "jimly" / "sample_logs_and_traces.jsonl"


@dataclass
class TraceRecord:
    """Satu baris trace lengkap untuk satu request API/UI."""

    request_id: str
    timestamp: str
    source: str
    config_id: str
    question: str
    travel_date: str
    verdict: str
    fallback_used: bool
    fallback_reason: str | None
    pii_redacted: bool
    prompt_tokens: int
    output_tokens: int
    stages_ms: dict[str, float] = field(default_factory=dict)
    total_latency_ms: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RequestTracer:
    """Mengukur waktu tiap tahap request dan menuliskannya ke log JSONL."""

    def __init__(
        self,
        *,
        config_id: str,
        question: str,
        travel_date: str,
        source: str = "api",
        log_path: str | Path = DEFAULT_TRACE_LOG_PATH,
    ) -> None:
        self.request_id = str(uuid.uuid4())
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.source = source
        self.config_id = config_id
        self.question = question
        self.travel_date = travel_date
        self.log_path = Path(log_path)
        self._started = time.perf_counter()
        self._stages_ms: dict[str, float] = {}

    def start_stage(self) -> float:
        return time.perf_counter()

    def end_stage(self, name: str, stage_started: float) -> float:
        elapsed_ms = round((time.perf_counter() - stage_started) * 1000.0, 2)
        self._stages_ms[name] = elapsed_ms
        return elapsed_ms

    def finish(
        self,
        *,
        verdict: str,
        fallback_used: bool = False,
        fallback_reason: str | None = None,
        pii_redacted: bool = False,
        prompt_tokens: int = 0,
        output_tokens: int = 0,
        error: str | None = None,
    ) -> TraceRecord:
        total_ms = round((time.perf_counter() - self._started) * 1000.0, 2)
        record = TraceRecord(
            request_id=self.request_id,
            timestamp=self.timestamp,
            source=self.source,
            config_id=self.config_id,
            question=self.question,
            travel_date=self.travel_date,
            verdict=verdict,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            pii_redacted=pii_redacted,
            prompt_tokens=prompt_tokens,
            output_tokens=output_tokens,
            stages_ms=dict(self._stages_ms),
            total_latency_ms=total_ms,
            error=error,
        )
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        return record
