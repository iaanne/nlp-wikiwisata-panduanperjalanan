import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, TypedDict


class Passage(TypedDict, total=False):
    passage_id: str
    chunk_id: str
    text: str
    score: float
    section: str | None
    lastedit: str | None
    lat: str | float | None
    lon: str | float | None
    latitude: str | float | None
    longitude: str | float | None
    city: str | None
    category: str | None


def _tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)


def _canonical_hash(
    chunks: list[dict[str, Any]],
    embedding_model: str,
    embedding_model_revision: str | None,
) -> str:
    encoded = json.dumps(
        {
            "chunks": chunks,
            "embedding_model": embedding_model,
            "embedding_model_revision": embedding_model_revision,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class Retriever:
    def __init__(
        self,
        chunks: list[dict[str, Any]],
        embedding_model: str = "intfloat/multilingual-e5-small",
        embedding_model_revision: str | None = None,
        dense_vectors: Any = None,
        reranker_model: str | None = None,
        cache_path: str | Path = "data/retrieval_cache.jsonl",
    ) -> None:
        self.chunks = chunks
        self.embedding_model = embedding_model
        self.embedding_model_revision = embedding_model_revision
        self.dense_vectors = dense_vectors
        self.reranker_model = reranker_model
        self.cache_path = Path(cache_path)
        self._encoder = None
        self._reranker = None
        self._hash = _canonical_hash(
            chunks, embedding_model, embedding_model_revision
        )
        self._tokenized = [_tokens(chunk["text"]) for chunk in chunks]
        self._lengths = [len(tokens) for tokens in self._tokenized]
        self._average_length = sum(self._lengths) / max(1, len(self._lengths))
        document_frequency: dict[str, int] = {}
        for tokens in self._tokenized:
            for token in set(tokens):
                document_frequency[token] = document_frequency.get(token, 0) + 1
        self._idf = {
            token: math.log(
                1 + (len(chunks) - frequency + 0.5) / (frequency + 0.5)
            )
            for token, frequency in document_frequency.items()
        }

    def index_hash(self) -> str:
        return self._hash

    def _model(self, reranker: bool = False):
        try:
            from sentence_transformers import CrossEncoder, SentenceTransformer
        except ImportError as error:
            raise RuntimeError(
                "Dense retrieval/reranking needs the optional sentence-transformers "
                "dependency. Install the project with `uv sync`."
            ) from error
        if reranker:
            if not self.reranker_model:
                raise ValueError("Set a reranker_model before requesting reranking.")
            if self._reranker is None:
                self._reranker = CrossEncoder(self.reranker_model)
            return self._reranker
        if self._encoder is None:
            model_options = (
                {"revision": self.embedding_model_revision}
                if self.embedding_model_revision is not None
                else {}
            )
            self._encoder = SentenceTransformer(self.embedding_model, **model_options)
        return self._encoder

    def encode_chunks(self):
        import numpy as np

        encoder = self._model()
        passages = [f"passage: {chunk['text']}" for chunk in self.chunks]
        return np.asarray(
            encoder.encode(
                passages,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=True,
            ),
            dtype="float32",
        )

    def _dense_scores(self, query: str) -> list[float]:
        import numpy as np

        vectors = self.dense_vectors
        if vectors is None:
            vectors = self.encode_chunks()
            self.dense_vectors = vectors
        query_vector = self._model().encode(
            [f"query: {query}"],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )[0]
        return np.asarray(vectors @ query_vector, dtype="float32").tolist()

    def _bm25_scores(self, query: str) -> list[float]:
        query_tokens = _tokens(query)
        scores: list[float] = []
        k1, b = 1.5, 0.75
        for tokens, length in zip(self._tokenized, self._lengths):
            frequencies: dict[str, int] = {}
            for token in tokens:
                frequencies[token] = frequencies.get(token, 0) + 1
            score = 0.0
            for token in query_tokens:
                frequency = frequencies.get(token, 0)
                if frequency:
                    denominator = frequency + k1 * (
                        1 - b + b * length / max(self._average_length, 1)
                    )
                    score += self._idf.get(token, 0) * (
                        frequency * (k1 + 1) / denominator
                    )
            scores.append(score)
        return scores

    def _read_cache(self, key: str) -> list[dict[str, Any]] | None:
        if not self.cache_path.exists():
            return None
        with self.cache_path.open(encoding="utf-8") as file:
            for line in file:
                record = json.loads(line)
                if record.get("cache_key") == key:
                    return record["results"]
        return None

    def _write_cache(self, key: str, results: list[dict[str, Any]]) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self.cache_path.open("a", encoding="utf-8") as file:
            file.write(
                json.dumps(
                    {"cache_key": key, "index_hash": self._hash, "results": results},
                    ensure_ascii=False,
                )
                + "\n"
            )

    def search(
        self,
        query: str,
        method: str = "hybrid",
        top_k: int | None = None,
        k: int = 5,
        filters: dict[str, Any] | None = None,
        city: str | None = None,
        category: str | None = None,
        rerank: bool = False,
        candidate_k: int = 20,
    ) -> list[Passage]:
        if top_k is not None:
            k = top_k
        if filters:
            city = filters.get("city", city)
            category = filters.get("category", category)
        if not query.strip():
            raise ValueError("query must not be empty.")
        if method not in {"bm25", "dense", "hybrid"}:
            raise ValueError(f"Unknown retrieval method: {method}")
        if k < 1 or candidate_k < 1:
            raise ValueError("k/top_k and candidate_k must be positive.")
        cache_payload = {
            "index_hash": self._hash,
            "query": query,
            "method": method,
            "k": k,
            "city": city,
            "category": category,
            "rerank": rerank,
            "candidate_k": candidate_k,
        }
        cache_key = hashlib.sha256(
            json.dumps(cache_payload, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()
        cached = self._read_cache(cache_key)
        if cached is not None:
            return cached

        eligible = [
            index
            for index, chunk in enumerate(self.chunks)
            if (city is None or str(chunk.get("city", "")).casefold() == city.casefold())
            and (
                category is None
                or str(chunk.get("category", "")).casefold() == category.casefold()
            )
        ]
        if not eligible:
            return []
        score_by_method: dict[str, list[float]] = {}
        if method in {"bm25", "hybrid"}:
            score_by_method["bm25"] = self._bm25_scores(query)
        if method in {"dense", "hybrid"}:
            score_by_method["dense"] = self._dense_scores(query)

        if method == "hybrid":
            rankings = {
                name: sorted(
                    eligible, key=lambda index: scores[index], reverse=True
                )[:candidate_k]
                for name, scores in score_by_method.items()
            }
            fused: dict[int, float] = {}
            for ranking in rankings.values():
                for rank, index in enumerate(ranking, start=1):
                    fused[index] = fused.get(index, 0.0) + 1 / (60 + rank)
            ranked = sorted(fused, key=fused.get, reverse=True)
            final_scores = fused
        else:
            scores = score_by_method[method]
            ranked = sorted(eligible, key=lambda index: scores[index], reverse=True)[
                :candidate_k
            ]
            final_scores = {index: scores[index] for index in ranked}

        ranked = ranked[:candidate_k]
        if rerank:
            reranker = self._model(reranker=True)
            pairs = [(query, self.chunks[index]["text"]) for index in ranked]
            rerank_scores = [float(score) for score in reranker.predict(pairs)]
            reranked = sorted(
                zip(rerank_scores, ranked), key=lambda pair: pair[0], reverse=True
            )
            ranked = [index for _, index in reranked]
            final_scores.update({index: score for score, index in reranked})
        results: list[Passage] = []
        for index in ranked[:k]:
            chunk = self.chunks[index]
            listing = chunk.get("listing") or {}
            passage: Passage = {
                **chunk,
                "passage_id": str(chunk.get("chunk_id") or chunk.get("passage_id")),
                "score": float(final_scores[index]),
                "section": chunk.get("section"),
                "lastedit": chunk.get("lastedit") or listing.get("lastedit"),
                "lat": chunk.get("lat") or chunk.get("latitude") or listing.get("latitude"),
                "lon": chunk.get("lon") or chunk.get("longitude") or listing.get("longitude"),
            }
            results.append(passage)
        self._write_cache(cache_key, results)
        return results
