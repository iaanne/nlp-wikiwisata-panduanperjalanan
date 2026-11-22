from pathlib import Path

import yaml

from wikiwisata.experiments.config import load_config

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT / "configs/experiments"
ABLATIONS = ROOT / "configs/ablations"


def test_all_experiments_share_base_model() -> None:
    configs = [
        load_config(path)
        for path in sorted(EXPERIMENTS.glob("b*.yaml"))
    ]
    model_ids = {config["model"]["id"] for config in configs}
    assert len(model_ids) == 1


def test_b2_and_b3_reuse_b1_prompt() -> None:
    b1 = load_config(EXPERIMENTS / "b1_structured_abstain.yaml")
    b2 = load_config(EXPERIMENTS / "b2_retrieval_variant.yaml")
    b3 = load_config(EXPERIMENTS / "b3_metadata_filtered.yaml")
    assert b2["prompt"] == b1["prompt"]
    assert b3["prompt"] == b1["prompt"]


def test_ablation_variants_change_one_key() -> None:
    for path in sorted(ABLATIONS.glob("a*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for variant in data["variants"]:
            assert len(variant["changed"]) == 1, (
                f"{path.name}:{variant['name']} mengubah lebih dari satu variabel"
            )
