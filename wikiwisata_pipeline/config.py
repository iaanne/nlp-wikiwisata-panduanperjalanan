import json
from pathlib import Path
from typing import Any


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8-sig") as file:
        config = json.load(file)
    if not config.get("api_url"):
        raise ValueError("Set api_url in the config to the MediaWiki API endpoint.")
    if not isinstance(config.get("articles"), list) or not config["articles"]:
        raise ValueError("Set articles to a non-empty list in the config.")
    return config
