import re
from typing import Any


def _words(text: str) -> list[str]:
    return re.findall(r"\S+", text)


def _listing_text(item: dict[str, Any]) -> str:
    fields = (
        ("Nama", "name"),
        ("Alamat", "address"),
        ("Telepon", "phone"),
        ("Jam", "hours"),
        ("Harga", "price"),
        ("Koordinat", "coordinates"),
        ("Latitude", "latitude"),
        ("Longitude", "longitude"),
        ("Lastedit", "lastedit"),
    )
    return " | ".join(
        f"{label}: {item[key]}" for label, key in fields if item.get(key)
    )


def _base_metadata(article: dict[str, Any]) -> dict[str, Any]:
    return {
        "doc_id": article["doc_id"],
        "title": article["title"],
        "page_id": article["page_id"],
        "revision_id": article["revision_id"],
        "revision_timestamp": article["revision_timestamp"],
        "sha256": article["sha256"],
        "license": article.get("license", "CC BY-SA 4.0"),
        "city": article.get("city"),
    }


def chunk_article(
    article: dict[str, Any],
    strategy: str,
    max_words: int = 180,
    overlap_words: int = 30,
) -> list[dict[str, Any]]:
    metadata = _base_metadata(article)
    chunks: list[dict[str, Any]] = []
    if strategy == "fixed":
        text = "\n\n".join(
            f"{section['title']}\n{section['text']}"
            for section in article["sections"]
            if section["text"]
        )
        words = _words(text)
        step = max(1, max_words - overlap_words)
        for start in range(0, len(words), step):
            chunk_words = words[start : start + max_words]
            if not chunk_words:
                continue
            chunks.append(
                {
                    **metadata,
                    "chunk_id": f"{article['doc_id']}:fixed:{start}",
                    "strategy": strategy,
                    "category": article.get("category"),
                    "listing_id": None,
                    "text": " ".join(chunk_words),
                }
            )
    elif strategy == "section":
        for index, section in enumerate(article["sections"]):
            text = " ".join(part for part in (section["title"], section["text"]) if part)
            if text:
                chunks.append(
                    {
                        **metadata,
                        "chunk_id": f"{article['doc_id']}:section:{index}",
                        "strategy": strategy,
                        "section": section["title"],
                        "category": article.get("category"),
                        "listing_id": None,
                        "text": text,
                    }
                )
    elif strategy == "listing":
        for index, listing in enumerate(article["listings"]):
            text = _listing_text(listing)
            if text:
                chunks.append(
                    {
                        **metadata,
                        "chunk_id": f"{article['doc_id']}:listing:{index}",
                        "strategy": strategy,
                        "category": listing.get("category") or article.get("category"),
                        "listing_id": f"{article['doc_id']}:listing:{index}",
                        "listing": listing,
                        "text": text,
                    }
                )
    else:
        raise ValueError(f"Unknown chunking strategy: {strategy}")
    return chunks
