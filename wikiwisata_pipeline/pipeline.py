import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from .chunking import chunk_article
from .mediawiki import collect_snapshots
from .parsing import parse_article
from .retrieval import Retriever


STRATEGIES = ("fixed", "section", "listing")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def fetch(config: dict[str, Any], root: Path) -> int:
    return len(collect_snapshots(config, root))


def build(config: dict[str, Any], root: Path) -> dict[str, int]:
    snapshot_paths = sorted((root / "data" / "snapshots").glob("*.json"))
    if not snapshot_paths:
        raise FileNotFoundError("No snapshots found; run the fetch command first.")
    articles = []
    for path in snapshot_paths:
        with path.open(encoding="utf-8") as file:
            articles.append(parse_article(json.load(file)))
    _write_jsonl(root / "data" / "articles.jsonl", articles)

    stats: dict[str, int] = {"documents": len(articles)}
    for strategy in STRATEGIES:
        chunks = [
            chunk
            for article in articles
            for chunk in chunk_article(
                article,
                strategy,
                int(config.get("fixed_chunk_words", 180)),
                int(config.get("fixed_overlap_words", 30)),
            )
        ]
        _write_jsonl(root / "data" / f"chunks_{strategy}.jsonl", chunks)
        used_docs = {chunk["doc_id"] for chunk in chunks}
        used_listing_ids = {
            chunk["listing_id"] for chunk in chunks if chunk.get("listing_id")
        }
        stats[f"{strategy}_documents_used"] = len(used_docs)
        stats[f"{strategy}_listing_items_used"] = len(used_listing_ids)
        stats[f"{strategy}_chunks"] = len(chunks)
    with (root / "data" / "usage_counts.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            ["strategy", "documents_used", "listing_items_used", "chunks"]
        )
        for strategy in STRATEGIES:
            writer.writerow(
                [
                    strategy,
                    stats[f"{strategy}_documents_used"],
                    stats[f"{strategy}_listing_items_used"],
                    stats[f"{strategy}_chunks"],
                ]
            )
    return stats


def index(config: dict[str, Any], root: Path) -> dict[str, str]:
    index_dir = root / "data" / "indexes"
    index_dir.mkdir(parents=True, exist_ok=True)
    hashes = {}
    model = config.get("embedding_model", "intfloat/multilingual-e5-small")
    for strategy in STRATEGIES:
        chunks = _read_jsonl(root / "data" / f"chunks_{strategy}.jsonl")
        if not chunks:
            raise FileNotFoundError(f"No {strategy} chunks; run build first.")
        retriever = Retriever(chunks, embedding_model=model)
        vectors = retriever.encode_chunks()
        np.save(index_dir / f"{strategy}_dense.npy", vectors)
        _write_jsonl(index_dir / f"{strategy}_chunks.jsonl", chunks)
        metadata = {
            "index_hash": retriever.index_hash(),
            "embedding_model": model,
            "chunk_strategy": strategy,
            "chunk_count": len(chunks),
        }
        with (index_dir / f"{strategy}_index.json").open("w", encoding="utf-8") as file:
            json.dump(metadata, file, ensure_ascii=False, indent=2)
        hashes[strategy] = metadata["index_hash"]
    return hashes


def _context(results: list[dict[str, Any]], budget: int) -> list[dict[str, Any]]:
    selected = []
    used = 0
    for result in results:
        words = result["text"].split()
        remaining = budget - used
        if remaining <= 0:
            break
        if len(words) > remaining:
            result = {**result, "text": " ".join(words[:remaining])}
            words = words[:remaining]
        if words:
            selected.append(result)
            used += len(words)
    return selected


def _load_retriever(
    strategy: str, config: dict[str, Any], root: Path, cache: Path
) -> Retriever:
    index_dir = root / "data" / "indexes"
    metadata_path = index_dir / f"{strategy}_index.json"
    if not metadata_path.exists():
        raise FileNotFoundError("Run the index command before retrieval experiments.")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    chunks = _read_jsonl(index_dir / f"{strategy}_chunks.jsonl")
    vectors = np.load(index_dir / f"{strategy}_dense.npy")
    retriever = Retriever(
        chunks,
        embedding_model=metadata["embedding_model"],
        dense_vectors=vectors,
        reranker_model=config.get("reranker_model"),
        cache_path=cache,
    )
    if retriever.index_hash() != metadata["index_hash"]:
        raise ValueError(f"Index hash mismatch for strategy {strategy}.")
    return retriever


def run_experiments(config: dict[str, Any], root: Path) -> int:
    query_path = root / config.get("queries_path", "data/queries.json")
    queries = json.loads(query_path.read_text(encoding="utf-8-sig"))
    if not isinstance(queries, list) or not queries:
        raise ValueError("queries.json must contain a non-empty JSON list.")
    cache_path = root / "data" / "retrieval_cache.jsonl"
    cache_path.write_text("", encoding="utf-8")
    output_path = root / "data" / "retrieval_runs.jsonl"
    rows: list[dict[str, Any]] = []
    strategy = config.get("experiment_chunk_strategy", "listing")
    top_k = int(config.get("top_k", 5))
    rerank_candidates = int(config.get("reranker_candidate_k", 20))
    budgets = config.get("context_budgets_words", {"small": 256, "large": 1024})

    for chunk_strategy in STRATEGIES:
        retriever = _load_retriever(chunk_strategy, config, root, cache_path)
        for query in queries:
            result = retriever.search(query["query"], method="hybrid", top_k=top_k)
            rows.append(
                {
                    "experiment": "A1",
                    "variant": chunk_strategy,
                    "query_id": query["id"],
                    "query": query["query"],
                    "index_hash": retriever.index_hash(),
                    "results": result,
                }
            )

    retriever = _load_retriever(strategy, config, root, cache_path)
    for query in queries:
        filters = {
            "city": query.get("city"),
            "category": query.get("category"),
        }
        for method, rerank in (
            ("dense", False),
            ("bm25", False),
            ("hybrid", False),
            ("hybrid", True),
        ):
            result = retriever.search(
                query["query"],
                method=method,
                top_k=top_k,
                rerank=rerank,
                candidate_k=rerank_candidates,
                **filters,
            )
            rows.append(
                {
                    "experiment": "A2",
                    "variant": f"{method}{'_reranker' if rerank else ''}",
                    "query_id": query["id"],
                    "query": query["query"],
                    "index_hash": retriever.index_hash(),
                    "results": result,
                }
            )

        fixed = retriever.search(
            query["query"], method="hybrid", top_k=top_k, **filters
        )
        first = retriever.search(
            query["query"], method="hybrid", top_k=3, **filters
        )
        threshold = float(config.get("adaptive_score_threshold", 0.01))
        adaptive = first
        if not first or first[0]["score"] < threshold:
            adaptive = retriever.search(
                query["query"], method="hybrid", top_k=top_k * 2, **filters
            )
        for variant, result in (("fixed", fixed), ("adaptive", adaptive)):
            rows.append(
                {
                    "experiment": "A6",
                    "variant": variant,
                    "query_id": query["id"],
                    "query": query["query"],
                    "index_hash": retriever.index_hash(),
                    "results": result,
                }
            )

        context_results = retriever.search(
            query["query"], method="hybrid", top_k=top_k * 2, **filters
        )
        for budget_name, budget_words in budgets.items():
            rows.append(
                {
                    "experiment": "A7",
                    "variant": budget_name,
                    "context_budget_words": int(budget_words),
                    "query_id": query["id"],
                    "query": query["query"],
                    "index_hash": retriever.index_hash(),
                    "results": _context(context_results, int(budget_words)),
                }
            )

    _write_jsonl(output_path, rows)
    return len(rows)
