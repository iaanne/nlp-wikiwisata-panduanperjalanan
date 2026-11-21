import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _request_json(api_url: str, params: dict[str, str]) -> dict[str, Any]:
    url = f"{api_url}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "WikiWisataResearchPipeline/1.0"})
    try:
        with urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError(f"MediaWiki API request failed for {url}: {error}") from error
    if "error" in data:
        raise RuntimeError(f"MediaWiki API error for {url}: {data['error']}")
    return data


def fetch_revision(
    api_url: str, title: str | None = None, revision_id: str | None = None
) -> dict[str, Any]:
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "ids|timestamp|content",
        "rvslots": "main",
        "format": "json",
        "formatversion": "2",
    }
    if revision_id:
        params["revids"] = revision_id
    elif title:
        params["titles"] = title
    else:
        raise ValueError("Either title or revision_id must be provided.")
    return _request_json(api_url, params)


def _source_url(api_url: str, title: str, revision_id: str | None = None) -> str:
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "ids|timestamp|content",
        "rvslots": "main",
        "format": "json",
        "formatversion": "2",
    }
    if revision_id:
        params["revids"] = revision_id
    else:
        params["titles"] = title
    return f"{api_url}?{urlencode(params)}"


def _extract_page(data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str]:
    pages = data.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        raise ValueError("The requested MediaWiki page or revision was not found.")
    page = pages[0]
    revisions = page.get("revisions", [])
    if not revisions:
        raise ValueError(f"No revision data returned for page {page.get('title')!r}.")
    revision = revisions[0]
    content = revision.get("slots", {}).get("main", {}).get("content")
    if content is None:
        content = revision.get("slots", {}).get("main", {}).get("*")
    if content is None:
        raise ValueError(f"Revision {revision.get('revid')} has no main-slot content.")
    return page, revision, content


def collect_snapshots(config: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    api_url = config["api_url"]
    snapshot_dir = root / "data" / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    register_path = root / "data" / "source_register.jsonl"
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for article in config["articles"]:
        title = article["title"]
        response = fetch_revision(api_url, title=title)
        page, _, _ = _extract_page(response)
        revisions: list[tuple[str | None, dict[str, Any] | None]] = [(None, response)]
        for revision_id in article.get("conflict_revision_ids", []):
            revisions.append((str(revision_id), None))

        for revision_id, cached_response in revisions:
            if cached_response is None:
                cached_response = fetch_revision(api_url, revision_id=revision_id)
            source_page, revision, wikitext = _extract_page(cached_response)
            actual_revision_id = str(revision["revid"])
            if (str(source_page["pageid"]), actual_revision_id) in seen:
                continue
            seen.add((str(source_page["pageid"]), actual_revision_id))
            fetched_at = datetime.now(timezone.utc).isoformat()
            content_hash = hashlib.sha256(wikitext.encode("utf-8")).hexdigest()
            snapshot = {
                "source_url": _source_url(api_url, title, revision_id),
                "fetched_at": fetched_at,
                "title": source_page["title"],
                "page_id": source_page["pageid"],
                "revision_id": actual_revision_id,
                "revision_timestamp": revision["timestamp"],
                "sha256": content_hash,
                "city": article.get("city"),
                "category": article.get("category"),
                "raw_api_response": cached_response,
                "wikitext": wikitext,
            }
            filename = f"{source_page['pageid']}_{actual_revision_id}.json"
            snapshot_path = snapshot_dir / filename
            with snapshot_path.open("w", encoding="utf-8") as file:
                json.dump(snapshot, file, ensure_ascii=False, indent=2)
            records.append(
                {
                    "source_url": snapshot["source_url"],
                    "fetched_at": fetched_at,
                    "title": source_page["title"],
                    "page_id": source_page["pageid"],
                    "revision_id": actual_revision_id,
                    "revision_timestamp": revision["timestamp"],
                    "sha256": content_hash,
                    "snapshot_path": str(snapshot_path.relative_to(root)),
                }
            )
            time.sleep(float(config.get("request_delay_seconds", 0.1)))

    register_path.parent.mkdir(parents=True, exist_ok=True)
    with register_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
    return records
