from pathlib import Path

import pytest
from jsonschema import ValidationError

from wikiwisata.experiments.schema import validate

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/answer.schema.json"


def _answer() -> dict:
    return {
        "answer": "Keraton Yogyakarta buka pukul 08.00.",
        "claims": [
            {
                "claim_id": "c1",
                "text": "Keraton Yogyakarta buka pukul 08.00.",
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


def test_answered_answer_is_valid() -> None:
    validate(_answer(), SCHEMA)


def test_abstain_requires_reason() -> None:
    answer = _answer()
    answer["verdict"] = "abstain"
    answer["abstain_reason"] = None
    with pytest.raises(ValidationError):
        validate(answer, SCHEMA)


def test_unknown_claim_status_is_rejected() -> None:
    answer = _answer()
    answer["claims"][0]["status"] = "maybe"
    with pytest.raises(ValidationError):
        validate(answer, SCHEMA)
