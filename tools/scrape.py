import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("agent.tools.scrape")

SCRAPE_TOOL_DEF = {
    "name": "scrape_url",
    "description": (
        "Extract clean text content from a webpage URL. "
        "Use after search_web to read full articles or documentation pages."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The full URL to scrape (must start with http:// or https://)",
            },
            "max_chars": {
                "type": "integer",
                "description": "Maximum characters to return (default 5000)",
                "default": 5000,
            },
        },
        "required": ["url"],
    },
}


def scrape_url(url: str, max_chars: int = 5000) -> str:
    """Extract clean text from a webpage."""
    if not url.startswith(("http://", "https://")):
        return "Error: URL must start with http:// or https://"

    try:
        response = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove noise
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
            tag.decompose()

        # Prefer article/main content
        main = soup.find("article") or soup.find("main") or soup.find("body")
        text = main.get_text(separator="\n", strip=True) if main else soup.get_text(separator="\n", strip=True)

        # Clean up blank lines
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        clean = "\n".join(lines)[:max_chars]

        logger.info(f"[scrape_url] url='{url}' → {len(clean)} chars")
        return clean if clean else "No readable content found."

    except requests.HTTPError as e:
        logger.error(f"[scrape_url] HTTP error {e.response.status_code} for {url}")
        return f"HTTP error {e.response.status_code}: could not access {url}"
    except Exception as e:
        logger.error(f"[scrape_url] error: {e}")
        return f"Scraping error: {e}"
