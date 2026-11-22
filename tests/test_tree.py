from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "configs/base.yaml",
    "configs/experiments/b0_baseline.yaml",
    "configs/experiments/b1_structured_abstain.yaml",
    "configs/experiments/b2_retrieval_variant.yaml",
    "configs/experiments/b3_metadata_filtered.yaml",
    "configs/experiments/b4_planner_verifier.yaml",
    "configs/experiments/b5_lora_qlora.yaml",
    "configs/experiments/b6_agentic_tool.yaml",
    "configs/ablations/a1_chunking.yaml",
    "configs/ablations/a2_retriever_reranker.yaml",
    "configs/ablations/a3_verifier.yaml",
    "configs/ablations/a4_adapter.yaml",
    "configs/ablations/a5_tool_usage.yaml",
    "configs/ablations/a6_adaptive_retrieval.yaml",
    "configs/ablations/a7_context_budget.yaml",
    "prompts/registry.json",
    "schemas/answer.schema.json",
    "schemas/manifest.schema.json",
    "src/wikiwisata/retrieval/base.py",
    "src/wikiwisata/experiments/harness.py",
    "src/wikiwisata/experiments/pipeline.py",
    "tests/test_answer_schema.py",
]


def test_required_paths_exist() -> None:
    missing = [path for path in REQUIRED if not (ROOT / path).exists()]
    assert not missing, f"Path belum ada: {missing}"
