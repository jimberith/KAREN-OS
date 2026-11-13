"""External web search adapter with concise, source-attributed results."""

from __future__ import annotations

import asyncio
from typing import Any


async def search_web(query: str, limit: int = 5) -> list[dict[str, str]]:
    """Search the public web using DDGS; failures are returned to the caller."""
    query = query.strip()
    if not query:
        return []
    try:
        from ddgs import DDGS
    except ImportError as exc:
        raise RuntimeError("Web search dependency is missing. Install the [web] extra.") from exc

    def run_search() -> list[dict[str, str]]:
        results: list[dict[str, Any]] = DDGS().text(query, max_results=min(max(limit, 1), 8))
        cleaned = []
        for item in results:
            title = str(item.get("title", "")).strip()
            url = str(item.get("href", item.get("url", ""))).strip()
            snippet = str(item.get("body", item.get("snippet", ""))).strip()
            if title and url.startswith(("https://", "http://")):
                cleaned.append({"title": title, "url": url, "snippet": snippet})
        return cleaned

    return await asyncio.to_thread(run_search)
