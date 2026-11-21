import html
import re
from typing import Any


LISTING_TEMPLATES = {
    "listing",
    "listing2",
    "listing3",
    "see",
    "do",
    "eat",
    "drink",
    "buy",
    "sleep",
    "go",
}

FIELD_ALIASES = {
    "name": ("name", "nama", "1"),
    "address": ("address", "alamat"),
    "phone": ("phone", "telephone", "tel", "telepon", "nomor telepon"),
    "hours": ("hours", "opening_hours", "jam", "jam buka"),
    "price": ("price", "harga"),
    "coordinates": ("coordinates", "coordinate", "koordinat"),
    "latitude": ("lat", "latitude"),
    "longitude": ("long", "lon", "longitude"),
    "lastedit": ("lastedit", "last_edit", "last edited"),
}


def _split_top_level(text: str, delimiter: str) -> list[str]:
    pieces: list[str] = []
    start = 0
    braces = brackets = 0
    index = 0
    while index < len(text):
        if text.startswith("{{", index):
            braces += 1
            index += 2
            continue
        if text.startswith("}}", index):
            braces = max(0, braces - 1)
            index += 2
            continue
        if text.startswith("[[", index):
            brackets += 1
            index += 2
            continue
        if text.startswith("]]", index):
            brackets = max(0, brackets - 1)
            index += 2
            continue
        if text[index] == delimiter and braces == 0 and brackets == 0:
            pieces.append(text[start:index])
            start = index + 1
        index += 1
    pieces.append(text[start:])
    return pieces


def _templates(wikitext: str):
    index = 0
    while index < len(wikitext) - 1:
        if wikitext.startswith("{{", index):
            start = index
            depth = 1
            index += 2
            while index < len(wikitext) - 1 and depth:
                if wikitext.startswith("{{", index):
                    depth += 1
                    index += 2
                elif wikitext.startswith("}}", index):
                    depth -= 1
                    index += 2
                else:
                    index += 1
            if depth == 0:
                yield wikitext[start + 2 : index - 2]
            continue
        index += 1


def clean_wikitext(value: str) -> str:
    value = re.sub(r"<ref\b[^>]*>.*?</ref\s*>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<ref\b[^>]*/\s*>", " ", value, flags=re.I)
    value = re.sub(r"\{\{[^{}]*\}\}", " ", value)
    value = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", value)
    value = re.sub(r"\[\[([^\]]+)\]\]", r"\1", value)
    value = re.sub(r"\[https?://\S+\s+([^\]]+)\]", r"\1", value)
    value = re.sub(r"https?://\S+", " ", value)
    value = re.sub(r"'''?([^']+?)'''?", r"\1", value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip(" |;,\n\t")


def _template_parts(template: str) -> tuple[str, dict[str, str]]:
    parts = _split_top_level(template, "|")
    name = clean_wikitext(parts[0]).strip().lower().replace("_", " ")
    params: dict[str, str] = {}
    positional = 1
    for part in parts[1:]:
        pair = _split_top_level(part, "=")
        if len(pair) > 1:
            key = clean_wikitext(pair[0]).lower().replace("_", " ").strip()
            value = clean_wikitext("=".join(pair[1:]))
        else:
            key, value = str(positional), clean_wikitext(part)
            positional += 1
        params[key] = value
    return name, params


def parse_listings(wikitext: str, lastedit: str) -> list[dict[str, Any]]:
    listings: list[dict[str, Any]] = []
    section_matches = list(
        re.finditer(r"(?m)^\s*==+\s*(.*?)\s*==+\s*$", wikitext)
    )
    section_categories = [
        (match.start(), clean_wikitext(match.group(1)).lower())
        for match in section_matches
    ]

    for template_position, template in _templates_with_positions(wikitext):
        template_name, params = _template_parts(template)
        template_key = template_name.replace(" ", "")
        if template_key not in LISTING_TEMPLATES:
            continue
        current_category = "unknown"
        for section_position, section_category in section_categories:
            if section_position >= template_position:
                break
            if section_category in {"see", "do", "eat", "drink", "buy", "sleep", "go"}:
                current_category = section_category
        values: dict[str, str | None] = {}
        for field, aliases in FIELD_ALIASES.items():
            values[field] = next(
                (params[alias] for alias in aliases if params.get(alias)), None
            )
        category = template_key if template_key in LISTING_TEMPLATES else current_category
        if category in {"listing", "listing2", "listing3"}:
            category = current_category
        values.update(
            {
                "category": category,
                "lastedit": values.get("lastedit") or lastedit,
                "template": template_name,
            }
        )
        if values["name"] or any(
            values[field]
            for field in ("address", "phone", "hours", "price", "coordinates")
        ):
            listings.append(values)
    return listings


def _templates_with_positions(wikitext: str):
    index = 0
    while index < len(wikitext) - 1:
        if wikitext.startswith("{{", index):
            start = index
            depth = 1
            index += 2
            while index < len(wikitext) - 1 and depth:
                if wikitext.startswith("{{", index):
                    depth += 1
                    index += 2
                elif wikitext.startswith("}}", index):
                    depth -= 1
                    index += 2
                else:
                    index += 1
            if depth == 0:
                yield start, wikitext[start + 2 : index - 2]
            continue
        index += 1


def split_sections(wikitext: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"(?m)^(={2,6})\s*(.*?)\s*\1\s*$", wikitext))
    if not matches:
        return [("Introduction", wikitext)]
    sections: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        sections.append(("Introduction", wikitext[: matches[0].start()]))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(wikitext)
        sections.append((clean_wikitext(match.group(2)), wikitext[match.end() : end]))
    return sections


def parse_article(snapshot: dict[str, Any]) -> dict[str, Any]:
    wikitext = snapshot["wikitext"]
    listings = parse_listings(wikitext, snapshot["revision_timestamp"])
    sections = [
        {"title": title, "text": clean_wikitext(body)}
        for title, body in split_sections(wikitext)
    ]
    return {
        "doc_id": f"{snapshot['page_id']}:{snapshot['revision_id']}",
        "title": snapshot["title"],
        "page_id": snapshot["page_id"],
        "revision_id": snapshot["revision_id"],
        "revision_timestamp": snapshot["revision_timestamp"],
        "sha256": snapshot["sha256"],
        "city": snapshot.get("city"),
        "category": snapshot.get("category"),
        "sections": sections,
        "listings": listings,
    }
