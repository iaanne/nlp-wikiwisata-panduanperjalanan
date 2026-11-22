"""Tes kontrak API, fallback mode terbatas, UI HTML, dan pencatatan trace."""

from __future__ import annotations

import json
from pathlib import Path

from wikiwisata.experiments.schema import validate
from wikiwisata.serving.api import load_api_config, predict
from wikiwisata.serving.fallback import build_fallback_response
from wikiwisata.serving.ui_app import render_ui_html

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "answer.schema.json"


def test_load_api_config_defaults() -> None:
    cfg = load_api_config()
    assert cfg["host"] == "127.0.0.1"
    assert int(cfg["port"]) == 8000
    assert cfg["default_config"] == "B4"


def test_fallback_response_matches_answer_schema() -> None:
    resp = build_fallback_response(reason="Retrieval gagal", config_id="B4")
    validate(resp, SCHEMA_PATH)
    assert resp["verdict"] == "abstain"
    assert resp["abstain_reason"] == "Retrieval gagal"
    assert resp["meta"]["fallback"] is True


def test_predict_unready_stage_triggers_real_fallback_and_trace(tmp_path: Path) -> None:
    trace_file = tmp_path / "traces.jsonl"
    resp = predict(
        question="Jam buka Keraton Yogyakarta?",
        travel_date="2026-12-01",
        config_id="B4",
        source="pytest",
        trace_log_path=trace_file,
    )
    validate(resp, SCHEMA_PATH)
    assert resp["verdict"] == "abstain"
    assert resp["meta"]["fallback"] is True
    assert "request_id" in resp["meta"]

    lines = trace_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    trace = json.loads(lines[0])
    assert trace["request_id"] == resp["meta"]["request_id"]
    assert trace["config_id"] == "B4"
    assert trace["fallback_used"] is True
    assert trace["verdict"] == "abstain"


def test_predict_rejects_empty_question_and_bad_date(tmp_path: Path) -> None:
    trace_file = tmp_path / "traces.jsonl"

    empty_q = predict("", "2026-12-01", config_id="B0", trace_log_path=trace_file)
    validate(empty_q, SCHEMA_PATH)
    assert empty_q["verdict"] == "abstain"

    bad_date = predict("Jam buka?", "01-12-2026", config_id="B0", trace_log_path=trace_file)
    validate(bad_date, SCHEMA_PATH)
    assert bad_date["verdict"] == "abstain"


def test_ui_html_contains_required_elements() -> None:
    html_doc = render_ui_html(default_config="B4")
    assert "Wikiwisata" in html_doc
    assert 'id="abstain-indicator"' in html_doc
    assert 'id="citations-list"' in html_doc
    assert 'value="B4" selected' in html_doc
