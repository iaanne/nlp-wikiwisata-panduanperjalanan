import json
import tempfile
import unittest
from pathlib import Path

from wikiwisata_pipeline.chunking import chunk_article
from wikiwisata_pipeline.parsing import parse_listings
from wikiwisata_pipeline.retrieval import Retriever


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


if __name__ == "__main__":
    unittest.main()
