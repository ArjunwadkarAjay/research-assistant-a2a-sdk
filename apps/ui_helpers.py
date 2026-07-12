import re
from typing import Dict, List

IGNORED_PREFIXES = {
    "topic",
    "search status",
    "reason",
    "potential angle",
    "a2a handoff",
    "research for",
}


def parse_research_items(research_summary: str) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    for line in research_summary.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.startswith(("- ", "• ")):
            continue

        body = stripped[2:].strip()
        if not body:
            continue

        title = body
        content = ""
        if ":" in body:
            title_part, content_part = body.split(":", 1)
            title = title_part.strip()
            content = content_part.strip()

        normalized_title = re.sub(r"\s+", " ", title).strip()
        normalized_content = re.sub(r"\s+", " ", content).strip()

        if not normalized_title:
            continue
        lowered = normalized_title.lower()
        if lowered in IGNORED_PREFIXES:
            continue
        if lowered.startswith(tuple(IGNORED_PREFIXES)):
            continue

        items.append({"title": normalized_title, "content": normalized_content, "url": ""})
    return items
