import json
from pathlib import Path

import pytest
from jsonschema import ValidationError

from wikiwisata.experiments.parse import (
    ParseError,
    normalize_answer,
    parse_answer,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/answer.schema.json"

VALID = {
    "answer": "Keraton buka pukul 08.00.",
    "claims": [
        {
            "claim_id": "c1",
            "text": "Keraton buka pukul 08.00.",
            "status": "supported",
            "evidence_ids": ["p1"],
        }
    ],
    "citations": [
        {
            "passage_id": "p1",
            "doc_id": "Yogyakarta",
            "rev_id": 1,
            "title": "Yogyakarta",
            "section": "Lihat",
        }
    ],
    "verdict": "answered",
    "abstain_reason": None,
    "tool_calls": [],
    "meta": {
        "config_id": "B4",
        "prompt_id": "b4_answer",
        "prompt_version": "1.0.0",
    },
}


def test_valid_json():
    assert parse_answer(json.dumps(VALID), SCHEMA) == VALID


def test_code_fence():
    raw = "```json\n" + json.dumps(VALID) + "\n```"
    assert parse_answer(raw, SCHEMA) == VALID


def test_text_before_json():
    raw = "Berikut jawabannya:\n" + json.dumps(VALID)
    assert parse_answer(raw, SCHEMA) == VALID


def test_broken_json():
    with pytest.raises(ParseError):
        parse_answer("{rusak", SCHEMA)


def test_schema_violation():
    bad = dict(VALID)
    del bad["verdict"]
    with pytest.raises(ValidationError):
        parse_answer(json.dumps(bad), SCHEMA)


def test_normalize_fills_missing_empty_fields():
    data, normalized = normalize_answer({"verdict": "abstain"})
    assert data["citations"] == []
    assert data["tool_calls"] == []
    assert "citations" in normalized
