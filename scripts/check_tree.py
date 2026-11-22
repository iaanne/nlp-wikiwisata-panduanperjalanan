"""Periksa apakah struktur project lengkap."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README.md",
    "pyproject.toml",
    "Makefile",
    "configs/base.yaml",
    "configs/experiments",
    "configs/ablations",
    "configs/serving",
    "prompts/registry.json",
    "prompts/system",
    "prompts/modules",
    "prompts/few_shot",
    "schemas/answer.schema.json",
    "schemas/tool_args",
    "src/wikiwisata/corpus",
    "src/wikiwisata/retrieval",
    "src/wikiwisata/experiments",
    "src/wikiwisata/evaluation",
    "src/wikiwisata/serving",
    "tests",
    "data/benchmark",
    "data/registry",
    "data/training",
    "data/tool_fixtures",
    "data/red_team",
    "data/annotations",
    "data/indexes/index_manifest.json",
    "artifacts/elias",
    "artifacts/ian",
    "artifacts/nad",
    "artifacts/jimly",
    "docs/adr",
]


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).exists()]
    if missing:
        print("Path belum ada:")
        for path in missing:
            print(f"- {path}")
        return 1
    print(f"Struktur OK: {len(REQUIRED)} path wajib ada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
