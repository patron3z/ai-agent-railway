from .search import search_web, SEARCH_TOOL_DEF
from .scrape import scrape_url, SCRAPE_TOOL_DEF
from .calculator import run_python, CALCULATOR_TOOL_DEF

TOOLS = [SEARCH_TOOL_DEF, SCRAPE_TOOL_DEF, CALCULATOR_TOOL_DEF]

TOOL_HANDLERS = {
    "search_web": search_web,
    "scrape_url": scrape_url,
    "run_python": run_python,
}

__all__ = ["TOOLS", "TOOL_HANDLERS"]
