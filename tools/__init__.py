from .search import search_web, SEARCH_TOOL_DEF
from .scrape import scrape_url, SCRAPE_TOOL_DEF
from .calculator import run_python, CALCULATOR_TOOL_DEF
from .leads import extract_leads, export_leads_csv, EXTRACT_LEADS_TOOL_DEF, EXPORT_LEADS_CSV_TOOL_DEF
from .hunter import (
    find_emails_by_domain, find_email_by_name, verify_email,
    HUNTER_DOMAIN_TOOL_DEF, HUNTER_FIND_TOOL_DEF, HUNTER_VERIFY_TOOL_DEF,
)

TOOLS = [
    SEARCH_TOOL_DEF,
    SCRAPE_TOOL_DEF,
    EXTRACT_LEADS_TOOL_DEF,
    EXPORT_LEADS_CSV_TOOL_DEF,
    HUNTER_DOMAIN_TOOL_DEF,
    HUNTER_FIND_TOOL_DEF,
    HUNTER_VERIFY_TOOL_DEF,
    CALCULATOR_TOOL_DEF,
]

TOOL_HANDLERS = {
    "search_web": search_web,
    "scrape_url": scrape_url,
    "extract_leads": extract_leads,
    "export_leads_csv": export_leads_csv,
    "find_emails_by_domain": find_emails_by_domain,
    "find_email_by_name": find_email_by_name,
    "verify_email": verify_email,
    "run_python": run_python,
}

__all__ = ["TOOLS", "TOOL_HANDLERS"]
