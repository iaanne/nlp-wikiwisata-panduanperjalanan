import json
import tempfile
import unittest
from pathlib import Path

from wikiwisata.corpus.chunking import chunk_article
from wikiwisata.corpus.parsing import parse_article, parse_listings
from wikiwisata.retrieval import Retriever
from wikiwisata.cli import main as cli_main


class ParsingTests(unittest.TestCase):
    def test_listing_template_fields_and_nested_links(self):
        wikitext = """
== Eat ==
{{listing
| name = Warung [[Gudeg|Gudeg Bu Tini]]
| address = Jalan Malioboro 1
| phone = +62 123
| hours = 09:00-21:00
| price = Rp 20.000
| lat = -7.8
| long = 110.3
}}
"""
        listings = parse_listings(wikitext, "2024-01-02T00:00:00Z")
        self.assertEqual(len(listings), 1)
        self.assertEqual(listings[0]["name"], "Warung Gudeg Bu Tini")
        self.assertEqual(listings[0]["category"], "eat")
        self.assertEqual(listings[0]["latitude"], "-7.8")
        self.assertEqual(listings[0]["lastedit"], "2024-01-02T00:00:00Z")


class ChunkingTests(unittest.TestCase):
    def test_listing_strategy_preserves_filterable_city_and_category(self):
        article = {
            "doc_id": "1:2",
            "title": "Kota",
            "page_id": 1,
            "revision_id": "2",
            "revision_timestamp": "2024-01-02T00:00:00Z",
            "sha256": "abc",
            "city": "Kota",
            "category": "destination",
            "sections": [],
            "listings": [
                {"name": "Museum", "category": "see", "address": "Jalan A"}
            ],
        }
        chunks = chunk_article(article, "listing")
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["city"], "Kota")
        self.assertEqual(chunks[0]["category"], "see")


class RetrievalTests(unittest.TestCase):
    def test_bm25_search_filters_metadata_and_writes_cache(self):
        chunks = [
            {
                "chunk_id": "a",
                "city": "Jakarta",
                "category": "eat",
                "text": "nasi goreng restoran",
            },
            {
                "chunk_id": "b",
                "city": "Bandung",
                "category": "see",
                "text": "museum sejarah",
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            cache_path = Path(directory) / "retrieval_cache.jsonl"
            retriever = Retriever(chunks, cache_path=cache_path)
            results = retriever.search(
                "restoran nasi",
                method="bm25",
                city="Jakarta",
                category="eat",
            )
            self.assertEqual([result["chunk_id"] for result in results], ["a"])
            self.assertTrue(cache_path.exists())
            self.assertEqual(len(json.loads(cache_path.read_text().splitlines()[0])["results"]), 1)
            self.assertEqual(len(retriever.index_hash()), 64)

    def test_empty_query_is_rejected(self):
        retriever = Retriever([{"text": "konten"}])
        with self.assertRaises(ValueError):
            retriever.search("  ", method="bm25")

    def test_search_supports_k_filters_and_passage_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            retriever = Retriever(
                [
                    {
                        "chunk_id": "doc:1:listing:0",
                        "city": "Yogyakarta",
                        "category": "eat",
                        "text": "Gudeg",
                        "listing": {
                            "lastedit": "2024-01-02",
                            "latitude": "-7.8",
                            "longitude": "110.3",
                        },
                    }
                ],
                cache_path=Path(directory) / "cache.jsonl",
            )
            results = retriever.search(
                "Gudeg",
                k=5,
                filters={"city": "Yogyakarta", "category": "eat"},
                method="bm25",
            )
        self.assertEqual(results[0]["passage_id"], "doc:1:listing:0")
        self.assertEqual(results[0]["lastedit"], "2024-01-02")
        self.assertEqual(results[0]["lat"], "-7.8")
        self.assertEqual(results[0]["lon"], "110.3")


class RepositoryMetadataTests(unittest.TestCase):
    def test_license_and_posix_snapshot_paths(self):
        root = Path(__file__).resolve().parents[1]
        for line in (root / "data" / "source_register.jsonl").read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            self.assertEqual(record["license"], "CC BY-SA 4.0")
            self.assertNotIn("\\", record["snapshot_path"])
        article = parse_article(
            {
                "page_id": 1,
                "revision_id": "2",
                "title": "Kota",
                "revision_timestamp": "2024-01-02T00:00:00Z",
                "sha256": "abc",
                "wikitext": "== Sejarah ==\nKota bersejarah.",
            }
        )
        self.assertEqual(article["license"], "CC BY-SA 4.0")

    def test_canonical_hash_is_deterministic(self):
        chunks = [{"chunk_id": "a", "text": "konten"}]
        first = Retriever(chunks)
        second = Retriever(chunks)
        self.assertEqual(first.index_hash(), second.index_hash())
        pinned = Retriever(chunks, embedding_model_revision="0123456789abcdef")
        self.assertNotEqual(first.index_hash(), pinned.index_hash())

    def test_cli_module_imports(self):
        self.assertTrue(callable(cli_main))

    def test_query_benchmark_has_expected_schema_and_distribution(self):
        root = Path(__file__).resolve().parents[1]
        queries = json.loads((root / "data" / "queries.json").read_text(encoding="utf-8"))
        counts = {
            category: sum(query["category"] == category for query in queries)
            for category in ("eat", "see", "do", "sleep", "buy")
        }
        self.assertEqual(len(queries), 100)
        self.assertEqual(
            [query["id"] for query in queries],
            [f"q{index:03}" for index in range(1, 101)],
        )
        self.assertEqual(counts, {"eat": 25, "see": 25, "do": 20, "sleep": 15, "buy": 15})
        self.assertEqual(sum(query["city"] is None for query in queries), 12)
        self.assertTrue(
            all(
                set(query) == {"id", "query", "city", "category"}
                and query["category"] in counts
                and query["query"].strip()
                for query in queries
            )
        )


if __name__ == "__main__":
    unittest.main()
