import csv
import io
import json
import logging
import re
from typing import Any

logger = logging.getLogger("agent.tools.leads")

# ─── Tool definitions ─────────────────────────────────────────────────────────

EXTRACT_LEADS_TOOL_DEF = {
    "name": "extract_leads",
    "description": (
        "Extract structured leads (name, company, email, phone, website) from raw text. "
        "Use after scrape_url to isolate contact information from a page."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Raw text content to extract leads from",
            },
            "source_url": {
                "type": "string",
                "description": "URL where the text was scraped from (for attribution)",
                "default": "",
            },
        },
        "required": ["text"],
    },
}

EXPORT_LEADS_CSV_TOOL_DEF = {
    "name": "export_leads_csv",
    "description": (
        "Convert a list of leads to CSV format for download. "
        "Use when the user wants to export leads as a file."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "leads": {
                "type": "array",
                "description": "List of lead objects with fields: name, company, email, phone, website, source",
                "items": {"type": "object"},
            },
            "filename": {
                "type": "string",
                "description": "Name of the CSV file (default: leads.csv)",
                "default": "leads.csv",
            },
        },
        "required": ["leads"],
    },
}


# ─── Regex patterns ───────────────────────────────────────────────────────────

EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)

PHONE_PATTERNS = [
    # French formats
    re.compile(r"\b0[1-9](?:[\s.\-]?\d{2}){4}\b"),
    re.compile(r"\+33[\s.]?[1-9](?:[\s.\-]?\d{2}){4}\b"),
    # International
    re.compile(r"\+\d{1,3}[\s.\-]?\d{2,4}[\s.\-]?\d{2,4}[\s.\-]?\d{2,4}\b"),
]

WEBSITE_PATTERN = re.compile(
    r"\bhttps?://(?:www\.)?[A-Za-z0-9\-]+\.[A-Za-z]{2,}(?:/[^\s]*)?\b"
)

# Common spam/noreply emails to skip
SKIP_EMAIL_PATTERNS = re.compile(
    r"(noreply|no-reply|donotreply|example|test@|info@example|@sentry|@github|@w3\.org)",
    re.IGNORECASE,
)


# ─── Tool implementations ─────────────────────────────────────────────────────

def extract_leads(text: str, source_url: str = "") -> str:
    """Extract structured lead data from raw text using regex patterns."""
    leads: list[dict[str, Any]] = []

    # Extract emails
    emails = [
        e for e in EMAIL_PATTERN.findall(text)
        if not SKIP_EMAIL_PATTERNS.search(e)
    ]

    # Extract phones
    phones: list[str] = []
    for pattern in PHONE_PATTERNS:
        found = pattern.findall(text)
        phones.extend([p.strip() for p in found])

    # Extract websites
    websites = [
        w for w in WEBSITE_PATTERN.findall(text)
        if not any(skip in w for skip in ["facebook.com", "twitter.com", "instagram.com", "youtube.com"])
    ]

    # Build lead records — one per email found
    seen_emails: set[str] = set()
    for i, email in enumerate(emails):
        email_lower = email.lower()
        if email_lower in seen_emails:
            continue
        seen_emails.add(email_lower)

        # Try to extract company from email domain
        domain = email.split("@")[1] if "@" in email else ""
        company = domain.split(".")[0].capitalize() if domain else ""

        lead = {
            "name": "",
            "company": company,
            "email": email,
            "phone": phones[i] if i < len(phones) else (phones[0] if phones else ""),
            "website": next((w for w in websites if domain and domain in w), websites[0] if websites else ""),
            "source": source_url,
        }
        leads.append(lead)

    # If no emails found but phones exist, create lead with phone only
    if not leads and phones:
        for phone in phones[:5]:
            leads.append({
                "name": "",
                "company": "",
                "email": "",
                "phone": phone,
                "website": websites[0] if websites else "",
                "source": source_url,
            })

    if not leads:
        logger.info(f"[extract_leads] No leads found from {source_url or 'text'}")
        return json.dumps({"leads": [], "count": 0, "message": "No leads found in this content."})

    logger.info(f"[extract_leads] Found {len(leads)} leads from {source_url or 'text'}")
    return json.dumps({"leads": leads, "count": len(leads)}, ensure_ascii=False, indent=2)


# In-memory lead store for CSV export
_lead_store: list[dict] = []


def export_leads_csv(leads: list[dict], filename: str = "leads.csv") -> str:
    """Convert leads list to CSV and store for download."""
    global _lead_store

    if not leads:
        return "No leads to export."

    # Store for /leads/download endpoint
    _lead_store = leads

    # Generate CSV preview
    fieldnames = ["name", "company", "email", "phone", "website", "source"]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for lead in leads:
        writer.writerow({k: lead.get(k, "") for k in fieldnames})

    csv_content = output.getvalue()
    logger.info(f"[export_leads_csv] Exported {len(leads)} leads")

    return (
        f"CSV prêt avec {len(leads)} leads.\n"
        f"**Télécharger :** /leads/download\n\n"
        f"Aperçu (5 premiers):\n```\n{csv_content[:800]}\n```"
    )


def get_lead_store() -> list[dict]:
    return _lead_store
