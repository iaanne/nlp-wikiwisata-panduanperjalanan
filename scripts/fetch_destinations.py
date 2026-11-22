import argparse
import json
import time
import urllib.parse
import urllib.request
from urllib.error import HTTPError
from pathlib import Path
from typing import Any

import yaml


API_URL = "https://id.wikivoyage.org/w/api.php"
CONFLICT_TITLE = "Yogyakarta"
CONFLICT_REVISION_IDS = ("35263", "38824")


def request_json(params: dict[str, str]) -> dict[str, Any]:
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "WikiWisataCorpusBuilder/1.0 (research dataset)"},
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
            break
        except HTTPError as error:
            if error.code != 429 or attempt == 3:
                raise
            retry_after = error.headers.get("Retry-After")
            delay = int(retry_after) if retry_after and retry_after.isdigit() else 2**attempt * 5
            print(f"Wikivoyage rate limit; waiting {delay}s before retry.")
            time.sleep(delay)
    if "error" in data:
        raise RuntimeError(f"MediaWiki API error: {data['error']}")
    return data


def get_articles(target_count: int) -> list[dict[str, Any]]:
    articles: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    continuation: str | None = None

    while len(articles) < target_count:
        params = {
            "action": "query",
            "list": "allpages",
            "apnamespace": "0",
            "apfilterredir": "nonredirects",
            "aplimit": "100",
            "format": "json",
            "formatversion": "2",
        }
        if continuation:
            params["apcontinue"] = continuation
        data = request_json(params)
        for page in data.get("query", {}).get("allpages", []):
            title = page["title"]
            if "/" in title or title.casefold().startswith("wisata:"):
                continue
            if title in seen_titles:
                continue
            seen_titles.add(title)
            articles.append(
                {
                    "title": title,
                    "city": title,
                    "category": "destination",
                    "conflict_revision_ids": [],
                }
            )
            if len(articles) == target_count:
                break

        continuation = data.get("continue", {}).get("apcontinue")
        if not continuation:
            break
        time.sleep(0.1)

    if len(articles) < target_count:
        raise RuntimeError(
            f"Only found {len(articles)} eligible pages; "
            f"{target_count} were requested."
        )
    return articles


def validate_conflict_revisions() -> None:
    data = request_json(
        {
            "action": "query",
            "prop": "revisions",
            "rvprop": "ids",
            "revids": "|".join(CONFLICT_REVISION_IDS),
            "format": "json",
            "formatversion": "2",
        }
    )
    pages = data.get("query", {}).get("pages", [])
    found = {
        str(revision["revid"]): page["title"]
        for page in pages
        for revision in page.get("revisions", [])
    }
    expected = {revision_id: CONFLICT_TITLE for revision_id in CONFLICT_REVISION_IDS}
    if found != expected:
        raise ValueError(
            f"Conflict revisions do not all belong to {CONFLICT_TITLE}: {found}"
        )


def update_config(config_path: Path, target_count: int) -> None:
    articles = get_articles(target_count)
    validate_conflict_revisions()

    articles = [article for article in articles if article["title"] != CONFLICT_TITLE]
    articles.insert(
        0,
        {
            "title": CONFLICT_TITLE,
            "city": CONFLICT_TITLE,
            "category": "destination",
            "conflict_revision_ids": list(CONFLICT_REVISION_IDS),
        },
    )
    articles = articles[:target_count]

    with config_path.open(encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}
    config["api_url"] = API_URL
    config["articles"] = articles
    with config_path.open("w", encoding="utf-8", newline="\n") as file:
        yaml.safe_dump(config, file, allow_unicode=True, sort_keys=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Populate the pipeline config with Wikivoyage page candidates."
    )
    parser.add_argument("--target-count", type=int, default=320)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/pipeline.yaml"),
    )
    args = parser.parse_args()
    if args.target_count < 300:
        parser.error("--target-count must be at least 300.")
    update_config(args.config, args.target_count)
    print(f"Configured {args.target_count} page candidates in {args.config}.")


if __name__ == "__main__":
    main()
