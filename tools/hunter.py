import logging
import os
import requests

logger = logging.getLogger("agent.tools.hunter")

HUNTER_DOMAIN_TOOL_DEF = {
    "name": "find_emails_by_domain",
    "description": (
        "Find professional email addresses for a company domain using Hunter.io. "
        "Use when you have a company website and want to find contact emails. "
        "Returns names, emails, and job titles of people at that company."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "domain": {
                "type": "string",
                "description": "Company domain (e.g. 'apple.com', 'tesla.com')",
            },
            "limit": {
                "type": "integer",
                "description": "Max emails to return (default 10)",
                "default": 10,
            },
        },
        "required": ["domain"],
    },
}

HUNTER_FIND_TOOL_DEF = {
    "name": "find_email_by_name",
    "description": (
        "Find the professional email of a specific person at a company using Hunter.io. "
        "Use when you know the person's name and their company domain."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "first_name": {
                "type": "string",
                "description": "Person's first name",
            },
            "last_name": {
                "type": "string",
                "description": "Person's last name",
            },
            "domain": {
                "type": "string",
                "description": "Company domain (e.g. 'company.com')",
            },
        },
        "required": ["first_name", "last_name", "domain"],
    },
}

HUNTER_VERIFY_TOOL_DEF = {
    "name": "verify_email",
    "description": (
        "Verify if an email address is valid and deliverable using Hunter.io. "
        "Use to validate emails before adding them to your leads list."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "Email address to verify",
            },
        },
        "required": ["email"],
    },
}


def _get_api_key() -> str:
    key = os.getenv("HUNTER_API_KEY", "")
    if not key:
        raise ValueError("HUNTER_API_KEY not configured")
    return key


def find_emails_by_domain(domain: str, limit: int = 10) -> str:
    """Find all emails for a company domain via Hunter.io."""
    try:
        api_key = _get_api_key()
        response = requests.get(
            "https://api.hunter.io/v2/domain-search",
            params={
                "domain": domain,
                "limit": min(limit, 100),
                "api_key": api_key,
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json().get("data", {})

        emails = data.get("emails", [])
        if not emails:
            return f"No emails found for domain '{domain}'."

        results = []
        for e in emails[:limit]:
            parts = []
            if e.get("first_name") or e.get("last_name"):
                parts.append(f"**{e.get('first_name', '')} {e.get('last_name', '')}**.strip()")
            if e.get("position"):
                parts.append(e["position"])
            parts.append(f"Email: {e['value']}")
            if e.get("confidence"):
                parts.append(f"Confiance: {e['confidence']}%")
            results.append(" | ".join(parts))

        org = data.get("organization", domain)
        logger.info(f"[hunter] domain={domain} → {len(emails)} emails")
        return f"**{org}** — {len(emails)} email(s) trouvé(s):\n\n" + "\n".join(results)

    except ValueError as e:
        return str(e)
    except Exception as e:
        logger.error(f"[hunter] find_emails_by_domain error: {e}")
        return f"Erreur Hunter.io: {e}"


def find_email_by_name(first_name: str, last_name: str, domain: str) -> str:
    """Find email for a specific person at a company."""
    try:
        api_key = _get_api_key()
        response = requests.get(
            "https://api.hunter.io/v2/email-finder",
            params={
                "domain": domain,
                "first_name": first_name,
                "last_name": last_name,
                "api_key": api_key,
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json().get("data", {})

        email = data.get("email")
        if not email:
            return f"Email non trouvé pour {first_name} {last_name} @ {domain}."

        confidence = data.get("score", 0)
        sources = len(data.get("sources", []))

        logger.info(f"[hunter] find {first_name} {last_name}@{domain} → {email}")
        return (
            f"**Email trouvé:** {email}\n"
            f"Confiance: {confidence}% | Sources: {sources}"
        )

    except ValueError as e:
        return str(e)
    except Exception as e:
        logger.error(f"[hunter] find_email_by_name error: {e}")
        return f"Erreur Hunter.io: {e}"


def verify_email(email: str) -> str:
    """Verify if an email is valid and deliverable."""
    try:
        api_key = _get_api_key()
        response = requests.get(
            "https://api.hunter.io/v2/email-verifier",
            params={"email": email, "api_key": api_key},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json().get("data", {})

        status = data.get("status", "unknown")
        score = data.get("score", 0)
        disposable = data.get("disposable", False)
        accept_all = data.get("accept_all", False)

        emoji = {"valid": "✅", "invalid": "❌", "accept_all": "⚠️", "unknown": "❓"}.get(status, "❓")

        logger.info(f"[hunter] verify {email} → {status} ({score}%)")
        return (
            f"{emoji} **{email}** — {status.upper()}\n"
            f"Score: {score}% | "
            f"Jetable: {'Oui' if disposable else 'Non'} | "
            f"Accept-all: {'Oui' if accept_all else 'Non'}"
        )

    except ValueError as e:
        return str(e)
    except Exception as e:
        logger.error(f"[hunter] verify_email error: {e}")
        return f"Erreur Hunter.io: {e}"
