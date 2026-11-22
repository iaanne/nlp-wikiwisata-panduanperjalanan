from pathlib import Path

from wikiwisata.experiments.manifest import (
    build_manifest,
    canonical_json,
    sha256_text,
)
from wikiwisata.experiments.schema import validate

ROOT = Path(__file__).resolve().parents[1]


def test_canonical_json_is_stable() -> None:
    left = {"b": 1, "a": 2}
    right = {"a": 2, "b": 1}
    assert canonical_json(left) == canonical_json(right)
    assert sha256_text(canonical_json(left)) == sha256_text(canonical_json(right))


def test_manifest_has_required_fields() -> None:
    manifest = build_manifest(
        config={"id": "B0", "model": {"id": "test"}, "decoding": {}},
        config_path="configs/experiments/b0_baseline.yaml",
        prompt_hashes={"b0_default": "abc"},
        index_hash=None,
        split="dev",
        split_hash=None,
        adapter_hash=None,
        seed=13,
        dry_run=True,
        run_id="test-run",
        repo_root=ROOT,
        created_at="2026-11-21T00:00:00Z",
    )

    assert manifest["run_id"] == "test-run"
    assert manifest["config_hash"]
    assert manifest["prompt_hashes"] == {"b0_default": "abc"}
    assert manifest["seed"] == 13
    assert manifest["dry_run"] is True
    validate(manifest, ROOT / "schemas/manifest.schema.json")
