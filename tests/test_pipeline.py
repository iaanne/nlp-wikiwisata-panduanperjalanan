from wikiwisata.experiments.pipeline import fill_template, summarize


def _result(parse_error=None, verdict="answered", answerable=True, claims=None):
    return {
        "id": "x",
        "slice": "easy",
        "answerable": answerable,
        "parse_error": parse_error,
        "output": (
            None
            if parse_error
            else {"verdict": verdict, "claims": claims or []}
        ),
        "normalized": [],
        "prompt_tokens": 10,
        "output_tokens": 5,
        "latency_ms": 100.0,
    }


def test_fill_template_keeps_json_braces():
    template = '{"a": 1, "question": "{question}"}'
    result = fill_template(template, {"question": "Halo"})
    assert result == '{"a": 1, "question": "Halo"}'


def test_summarize_counts_parse_and_abstain():
    results = [
        _result(verdict="answered", answerable=True),
        _result(verdict="abstain", answerable=False),
        _result(parse_error="ParseError: rusak", answerable=True),
    ]
    summary = summarize(results, "B0", "smoke", 13)

    assert summary["items"] == 3
    assert summary["parsed"] == 2
    assert summary["parse_failures"] == 1
    assert summary["abstain"] == 1
    assert summary["abstain_on_answerable"] == 0
    assert summary["abstain_on_unanswerable"] == 1


def test_summarize_counts_supported_without_evidence():
    results = [
        _result(
            claims=[
                {"claim_id": "c1", "text": "x", "status": "supported", "evidence_ids": []}
            ]
        )
    ]
    summary = summarize(results, "B1", "smoke", 13)
    assert summary["supported_without_evidence"] == 1
