from pathlib import Path

from wikiwisata.experiments.prompt_manager import load_registry, verify_hashes

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "prompts"


def test_prompt_hashes_match() -> None:
    registry = load_registry(PROMPTS)
    verify_hashes(PROMPTS, registry)


def test_registry_has_no_duplicate_ids() -> None:
    registry = load_registry(PROMPTS)
    ids = [entry["id"] for entry in registry["prompts"]]
    assert len(ids) == len(set(ids))
