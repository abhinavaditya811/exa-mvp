from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import sys

from research_assistant.search import run_search

# ---------------------------------------------------------------------------
# Output schemas — object type, one per pass
# ---------------------------------------------------------------------------

PROFILE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "canonical_name": {"type": "string"},
        "overview": {"type": "string"},
        "former_name": {"type": "string"},
        "founded_year": {"type": "string"},
        "headquarters": {"type": "string"},
        "employee_count": {"type": "string"},
        "ceo": {"type": "string"},
        "cto": {"type": "string"},
        "key_products": {"type": "string"},
    },
    "required": ["overview"],
}

FUNDING_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "latest_round": {"type": "string"},
        "latest_amount": {"type": "string"},
        "latest_date": {"type": "string"},
        "total_raised": {"type": "string"},
        "key_investors": {"type": "array", "items": {"type": "string"}},
        "valuation": {"type": "string"},
    },
}

NEWS_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "headlines": {"type": "array", "items": {"type": "string"}},
        "product_launches": {"type": "array", "items": {"type": "string"}},
    },
}

COMPETITORS_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "direct_competitors": {"type": "array", "items": {"type": "string"}},
        "competitive_landscape": {"type": "string"},
    },
}

HIRING_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "open_roles": {"type": "array", "items": {"type": "string"}},
        "hiring_teams": {"type": "array", "items": {"type": "string"}},
        "hiring_signals": {"type": "string"},
    },
}

CONTACTS_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "engineering_leads": {"type": "array", "items": {"type": "string"}},
        "recruiters": {"type": "array", "items": {"type": "string"}},
        "notable_engineers": {"type": "array", "items": {"type": "string"}},
    },
}

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class ProfileInfo:
    overview: str
    canonical_name: str | None
    former_name: str | None
    founded_year: str | None
    headquarters: str | None
    employee_count: str | None
    ceo: str | None
    cto: str | None
    key_products: str | None


@dataclass
class FundingInfo:
    latest_round: str | None
    latest_amount: str | None
    latest_date: str | None
    total_raised: str | None
    key_investors: list[str]
    valuation: str | None


@dataclass
class NewsInfo:
    headlines: list[str]
    product_launches: list[str]


@dataclass
class HiringInfo:
    open_roles: list[str]
    hiring_teams: list[str]
    hiring_signals: str | None


@dataclass
class ContactsInfo:
    engineering_leads: list[str]
    recruiters: list[str]
    notable_engineers: list[str]


@dataclass
class CompanyBrief:
    name: str
    profile: ProfileInfo | None
    funding: FundingInfo | None
    news: NewsInfo | None
    competitors: list[str]
    competitive_landscape: str | None
    hiring: HiringInfo | None
    contacts: ContactsInfo | None
    thin_sections: list[str]
    citations: dict[str, list[tuple[str, str]]]  # section → [(url, title)]

# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------


def _get_content(response: object) -> dict:
    output = getattr(response, "output", None)
    if output is None:
        return {}
    content = getattr(output, "content", None)
    return content if isinstance(content, dict) else {}


def _get_citations(response: object) -> list[tuple[str, str]]:
    output = getattr(response, "output", None)
    if output is None:
        return []
    seen: set[str] = set()
    result: list[tuple[str, str]] = []
    for g in getattr(output, "grounding", []) or []:
        for c in getattr(g, "citations", []):
            url = getattr(c, "url", "")
            if url and url not in seen:
                seen.add(url)
                result.append((url, getattr(c, "title", "")))
    return result


def _is_thin(response: object) -> bool:
    output = getattr(response, "output", None)
    if output is None:
        return True
    total = sum(
        len(getattr(g, "citations", []))
        for g in getattr(output, "grounding", []) or []
    )
    return total < 2

# ---------------------------------------------------------------------------
# Per-pass fetchers
# ---------------------------------------------------------------------------


def _fetch_profile(query: str, search_type: str) -> object:
    return run_search(
        f"{query} company overview founded headquarters employees leadership",
        num_results=5,
        search_type=search_type,
        output_schema=PROFILE_SCHEMA,
        category="company",
        include_domains=["crunchbase.com", "linkedin.com", "bloomberg.com", "wikipedia.org"],
    )


def _fetch_funding(query: str, search_type: str) -> object:
    # Broad domain list so freshly-announced rounds on TechCrunch/Reuters
    # aren't missed before Crunchbase indexes them.
    return run_search(
        f"{query} latest funding round raised investors valuation 2025 2026",
        num_results=8,
        search_type=search_type,
        output_schema=FUNDING_SCHEMA,
        include_domains=[
            "crunchbase.com", "pitchbook.com",
            "techcrunch.com", "axios.com",
            "bloomberg.com", "reuters.com",
            "businessinsider.com", "forbes.com",
            "a16z.com", "a16z.news",
        ],
    )


def _fetch_news(query: str, search_type: str, since_date: str) -> object:
    return run_search(
        f"{query} news announcements launches partnerships",
        num_results=8,
        search_type=search_type,
        output_schema=NEWS_SCHEMA,
        category="news",
        start_published_date=since_date,
    )


def _fetch_competitors(query: str, search_type: str) -> object:
    return run_search(
        f"{query} competitors alternatives vs comparison market",
        num_results=5,
        search_type=search_type,
        output_schema=COMPETITORS_SCHEMA,
    )


def _fetch_hiring(query: str, search_type: str) -> object:
    return run_search(
        f"{query} jobs hiring open roles engineering positions",
        num_results=5,
        search_type=search_type,
        output_schema=HIRING_SCHEMA,
        include_domains=["linkedin.com", "greenhouse.io", "lever.co", "ashbyhq.com", "wellfound.com"],
    )


def _fetch_contacts(query: str, search_type: str) -> object:
    return run_search(
        f"{query} engineering team leads recruiters employees",
        num_results=5,
        search_type=search_type,
        output_schema=CONTACTS_SCHEMA,
        category="people",
        include_domains=["linkedin.com"],
    )

# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------


def _prompt_clarification(company: str, section: str, attempt: int) -> str | None:
    hints = [
        f"Try the full legal name, a known domain (e.g. '{company.lower().replace(' ', '')}.com'), or add the industry.",
        f"Try adding context like '{company} startup' or '{company} AI company'.",
    ]
    print(f"\nLimited data found for '{company}' ({section}).", file=sys.stderr)
    print(f"Hint: {hints[attempt]}", file=sys.stderr)
    print("Enter a more specific query, or press Enter to skip: ", end="", file=sys.stderr, flush=True)
    value = input().strip()
    return value or None


def _suggest_manual(company: str, section: str) -> None:
    print(
        f"\n[{section}] Still no reliable data for '{company}'. "
        "Try searching manually on Crunchbase, LinkedIn, or PitchBook.",
        file=sys.stderr,
    )


def _fetch_with_retry(
    fetch_fn: Callable[[str], object],
    company: str,
    section: str,
) -> object | None:
    response = fetch_fn(company)
    if not _is_thin(response):
        return response

    for attempt in range(2):
        refined = _prompt_clarification(company, section, attempt)
        if refined is None:
            break
        response = fetch_fn(refined)
        if not _is_thin(response):
            return response

    _suggest_manual(company, section)
    return None

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def build_brief(
    company: str,
    search_type: str = "deep",
    since_days: int = 90,
    focus: str = "all",
) -> CompanyBrief:
    since_date = (datetime.now() - timedelta(days=since_days)).strftime("%Y-%m-%dT00:00:00Z")
    thin_sections: list[str] = []
    citations: dict[str, list[tuple[str, str]]] = {}

    # --- Profile + leadership ---
    profile: ProfileInfo | None = None
    if focus in ("all", "profile", "people"):
        resp = _fetch_with_retry(
            lambda q: _fetch_profile(q, search_type), company, "profile"
        )
        if resp:
            c = _get_content(resp)
            profile = ProfileInfo(
                overview=c.get("overview", ""),
                canonical_name=c.get("canonical_name"),
                former_name=c.get("former_name"),
                founded_year=c.get("founded_year"),
                headquarters=c.get("headquarters"),
                employee_count=c.get("employee_count"),
                ceo=c.get("ceo"),
                cto=c.get("cto"),
                key_products=c.get("key_products"),
            )
            citations["profile"] = _get_citations(resp)
        else:
            thin_sections.append("profile")

    # Use the canonical name from the profile pass for all subsequent queries so
    # that ambiguous inputs like "Listen" resolve to "Listen Labs" before hitting
    # news, funding, competitors, etc.
    query = (profile.canonical_name if profile and profile.canonical_name else None) or company

    # --- Funding ---
    funding: FundingInfo | None = None
    if focus in ("all", "funding"):
        resp = _fetch_with_retry(
            lambda q: _fetch_funding(q, search_type), query, "funding"
        )
        if resp:
            c = _get_content(resp)
            funding = FundingInfo(
                latest_round=c.get("latest_round"),
                latest_amount=c.get("latest_amount"),
                latest_date=c.get("latest_date"),
                total_raised=c.get("total_raised"),
                key_investors=c.get("key_investors") or [],
                valuation=c.get("valuation"),
            )
            citations["funding"] = _get_citations(resp)
        else:
            thin_sections.append("funding")

    # --- News ---
    news: NewsInfo | None = None
    if focus in ("all", "news"):
        resp = _fetch_with_retry(
            lambda q: _fetch_news(q, search_type, since_date), query, "news"
        )
        if resp:
            c = _get_content(resp)
            news = NewsInfo(
                headlines=c.get("headlines") or [],
                product_launches=c.get("product_launches") or [],
            )
            citations["news"] = _get_citations(resp)
        else:
            thin_sections.append("news")

    # --- Competitors ---
    competitors: list[str] = []
    landscape: str | None = None
    if focus in ("all", "competitors"):
        resp = _fetch_with_retry(
            lambda q: _fetch_competitors(q, search_type), query, "competitors"
        )
        if resp:
            c = _get_content(resp)
            competitors = c.get("direct_competitors") or []
            landscape = c.get("competitive_landscape")
            citations["competitors"] = _get_citations(resp)
        else:
            thin_sections.append("competitors")

    # --- Hiring signals ---
    hiring: HiringInfo | None = None
    if focus in ("all", "hiring"):
        resp = _fetch_with_retry(
            lambda q: _fetch_hiring(q, search_type), query, "hiring"
        )
        if resp:
            c = _get_content(resp)
            hiring = HiringInfo(
                open_roles=c.get("open_roles") or [],
                hiring_teams=c.get("hiring_teams") or [],
                hiring_signals=c.get("hiring_signals"),
            )
            citations["hiring"] = _get_citations(resp)
        else:
            thin_sections.append("hiring")

    # --- Contacts ---
    contacts: ContactsInfo | None = None
    if focus in ("all", "contacts", "people"):
        resp = _fetch_with_retry(
            lambda q: _fetch_contacts(q, search_type), query, "contacts"
        )
        if resp:
            c = _get_content(resp)
            contacts = ContactsInfo(
                engineering_leads=c.get("engineering_leads") or [],
                recruiters=c.get("recruiters") or [],
                notable_engineers=c.get("notable_engineers") or [],
            )
            citations["contacts"] = _get_citations(resp)
        else:
            thin_sections.append("contacts")

    return CompanyBrief(
        name=query,
        profile=profile,
        funding=funding,
        news=news,
        competitors=competitors,
        competitive_landscape=landscape,
        hiring=hiring,
        contacts=contacts,
        thin_sections=thin_sections,
        citations=citations,
    )
