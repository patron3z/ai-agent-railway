import logging
import os
import requests

logger = logging.getLogger("agent.tools.search")

SEARCH_TOOL_DEF = {
    "name": "search_web",
    "description": (
        "Search the web for current information. Use when you need up-to-date facts, "
        "news, or information you don't know. Returns titles, snippets and URLs."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to look up",
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return (default 5, max 10)",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}


def search_web(query: str, num_results: int = 5) -> str:
    """Search the web using Serper API. Falls back to DuckDuckGo if no API key."""
    api_key = os.getenv("SERPER_API_KEY", "")

    if api_key:
        return _search_serper(query, num_results, api_key)
    else:
        logger.warning("No SERPER_API_KEY found, using DuckDuckGo fallback")
        return _search_duckduckgo(query, num_results)


def _search_serper(query: str, num_results: int, api_key: str) -> str:
    try:
        response = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": api_key,
                "Content-Type": "application/json",
            },
            json={"q": query, "num": min(num_results, 10)},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

        results = []
        for r in data.get("organic", [])[:num_results]:
            results.append(
                f"**{r.get('title', 'No title')}**\n"
                f"{r.get('snippet', 'No description')}\n"
                f"URL: {r.get('link', '')}"
            )

        if not results:
            return "No results found."

        logger.info(f"[search_web] query='{query}' → {len(results)} results")
        return "\n\n".join(results)

    except Exception as e:
        logger.error(f"[search_web] Serper error: {e}")
        return f"Search error: {e}"


def _search_duckduckgo(query: str, num_results: int) -> str:
    """Fallback: DuckDuckGo Instant Answer API (limited but free)."""
    try:
        response = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": "1"},
            timeout=10,
        )
        data = response.json()

        parts = []
        if data.get("AbstractText"):
            parts.append(f"**Summary:** {data['AbstractText']}\nURL: {data.get('AbstractURL', '')}")

        for topic in data.get("RelatedTopics", [])[:num_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                parts.append(f"- {topic['Text']}\n  URL: {topic.get('FirstURL', '')}")

        if not parts:
            return f"No DuckDuckGo results for '{query}'. Consider adding a SERPER_API_KEY."

        logger.info(f"[search_web] DDG query='{query}' → {len(parts)} results")
        return "\n\n".join(parts)

    except Exception as e:
        logger.error(f"[search_web] DuckDuckGo error: {e}")
        return f"Search error: {e}"
