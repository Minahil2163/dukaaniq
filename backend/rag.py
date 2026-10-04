"""Small local retrieval layer for DukaanIQ retail knowledge."""
import json
import re
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
KB_PATH = BASE_DIR / "knowledge" / "retail_knowledge.json"


def _load() -> list[dict[str, Any]]:
    with KB_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def retrieve_knowledge(query: str, limit: int = 2) -> list[dict[str, Any]]:
    q = _tokens(query)
    scored = []
    for item in _load():
        hay = _tokens(" ".join([item["title"], item["topic"], item["text"]]))
        score = len(q & hay)
        if score:
            scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:limit]]
