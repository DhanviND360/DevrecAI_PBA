"""
DevRecAI Tools Database Loader.

Loads devrecai/data/tools.json and provides
filtering, lookup, and category-based access.
"""
from __future__ import annotations

import json
from pathlib import Path
from functools import lru_cache
from typing import Optional

_DATA_PATH = Path(__file__).parent.parent / "data" / "tools.json"


@lru_cache(maxsize=1)
def load_tools() -> list[dict]:
    """Load and cache all tools from the knowledge base."""
    if not _DATA_PATH.exists():
        return []
    with open(_DATA_PATH) as f:
        return json.load(f)


def get_tools_by_category(category: str) -> list[dict]:
    """Return all tools in a given category (case-insensitive substring match)."""
    cat_lower = category.lower()
    return [
        t for t in load_tools()
        if cat_lower in t.get("category", "").lower()
    ]


def get_tool_by_name(name: str) -> Optional[dict]:
    """Look up a tool by exact or case-insensitive name."""
    name_lower = name.lower()
    for t in load_tools():
        if t.get("name", "").lower() == name_lower:
            return t
    return None


def get_all_categories() -> list[str]:
    """Return sorted unique category names from the knowledge base."""
    cats = {t.get("category", "Unknown") for t in load_tools()}
    return sorted(cats)


def search_tools(query: str) -> list[dict]:
    """Full-text search across name, category, and tags."""
    q = query.lower()
    return [
        t for t in load_tools()
        if q in t.get("name", "").lower()
        or q in t.get("category", "").lower()
        or any(q in tag.lower() for tag in t.get("tags", []))
    ]
