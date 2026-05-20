import pytest
from unittest.mock import MagicMock

from research_assistant.intelligence import (
    build_brief,
    _is_thin,
    _get_content,
    _get_citations,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(content: dict, urls: list[str]) -> MagicMock:
    response = MagicMock()
    response.output.content = content
    cites = [MagicMock(url=u, title="Title") for u in urls]
    response.output.grounding = [MagicMock(citations=cites)]
    return response


def _thin_response() -> MagicMock:
    response = MagicMock()
    response.output.content = {}
    response.output.grounding = []
    return response


# ---------------------------------------------------------------------------
# Unit: helpers
# ---------------------------------------------------------------------------


def test_is_thin_no_output():
    r = MagicMock()
    r.output = None
    assert _is_thin(r) is True


def test_is_thin_zero_citations():
    assert _is_thin(_thin_response()) is True


def test_is_thin_enough_citations():
    r = _make_response({"overview": "x"}, ["https://a.com", "https://b.com"])
    assert _is_thin(r) is False


def test_get_content_returns_dict():
    r = _make_response({"ceo": "Alice"}, ["https://a.com", "https://b.com"])
    assert _get_content(r) == {"ceo": "Alice"}


def test_get_content_non_dict_returns_empty():
    r = MagicMock()
    r.output.content = "plain string"
    assert _get_content(r) == {}


def test_get_citations_deduplicates():
    r = MagicMock()
    cite = MagicMock(url="https://a.com", title="A")
    r.output.grounding = [
        MagicMock(citations=[cite]),
        MagicMock(citations=[cite]),
    ]
    cites = _get_citations(r)
    assert len(cites) == 1
    assert cites[0] == ("https://a.com", "A")


# ---------------------------------------------------------------------------
# Content fixtures
# ---------------------------------------------------------------------------

PROFILE_CONTENT = {
    "overview": "Neural search API.",
    "former_name": "Metaphor",
    "founded_year": "2022",
    "headquarters": "San Francisco",
    "employee_count": "~50",
    "ceo": "Will Bryk",
    "cto": None,
    "key_products": "Search API",
}

FUNDING_CONTENT = {
    "latest_round": "Series C",
    "latest_amount": "$250M",
    "latest_date": "2026-05-20",
    "total_raised": "$272M",
    "key_investors": ["a16z"],
    "valuation": "$2.2B",
}

NEWS_CONTENT = {
    "headlines": ["Launched deep-reasoning search"],
    "product_launches": [],
}

COMPETITORS_CONTENT = {
    "direct_competitors": ["Perplexity", "Tavily"],
    "competitive_landscape": "Competitive AI search space.",
}

HIRING_CONTENT = {
    "open_roles": ["Senior ML Engineer", "Backend Engineer"],
    "hiring_teams": ["Platform", "Search"],
    "hiring_signals": "Actively scaling post-Series C.",
}

CONTACTS_CONTENT = {
    "engineering_leads": ["Alice Smith (VP Eng)"],
    "recruiters": ["Bob Jones"],
    "notable_engineers": ["Carol Lee"],
}


# ---------------------------------------------------------------------------
# Integration: build_brief happy path
# ---------------------------------------------------------------------------


def test_build_brief_all_passes(monkeypatch):
    calls: list[str] = []

    def mock_search(query, **kwargs):
        calls.append(query)
        if "overview" in query or "leadership" in query:
            return _make_response(PROFILE_CONTENT, ["https://a.com", "https://b.com"])
        if "funding" in query or "investors" in query:
            return _make_response(FUNDING_CONTENT, ["https://c.com", "https://d.com"])
        if "news" in query:
            return _make_response(NEWS_CONTENT, ["https://e.com", "https://f.com"])
        if "competitors" in query:
            return _make_response(COMPETITORS_CONTENT, ["https://g.com", "https://h.com"])
        if "jobs" in query or "hiring" in query:
            return _make_response(HIRING_CONTENT, ["https://i.com", "https://j.com"])
        if "team leads" in query or "recruiters" in query:
            return _make_response(CONTACTS_CONTENT, ["https://k.com", "https://l.com"])
        return _make_response({}, [])

    monkeypatch.setattr("research_assistant.intelligence.run_search", mock_search)

    brief = build_brief("Exa AI", focus="all")

    assert len(calls) == 6
    assert brief.profile is not None
    assert brief.profile.former_name == "Metaphor"
    assert brief.profile.ceo == "Will Bryk"
    assert brief.funding is not None
    assert brief.funding.latest_round == "Series C"
    assert brief.funding.valuation == "$2.2B"
    assert brief.news is not None
    assert brief.competitors == ["Perplexity", "Tavily"]
    assert brief.hiring is not None
    assert brief.hiring.open_roles == ["Senior ML Engineer", "Backend Engineer"]
    assert brief.contacts is not None
    assert brief.contacts.engineering_leads == ["Alice Smith (VP Eng)"]
    assert brief.thin_sections == []


def test_build_brief_focus_limits_passes(monkeypatch):
    calls: list[str] = []

    def mock_search(query, **kwargs):
        calls.append(query)
        return _make_response(FUNDING_CONTENT, ["https://a.com", "https://b.com"])

    monkeypatch.setattr("research_assistant.intelligence.run_search", mock_search)

    brief = build_brief("Exa AI", focus="funding")

    assert len(calls) == 1
    assert brief.funding is not None
    assert brief.profile is None
    assert brief.news is None
    assert brief.hiring is None
    assert brief.contacts is None


def test_former_name_present_in_profile(monkeypatch):
    monkeypatch.setattr(
        "research_assistant.intelligence.run_search",
        lambda *a, **kw: _make_response(PROFILE_CONTENT, ["https://a.com", "https://b.com"]),
    )
    brief = build_brief("Exa AI", focus="profile")
    assert brief.profile is not None
    assert brief.profile.former_name == "Metaphor"


def test_canonical_name_used_for_subsequent_passes(monkeypatch):
    """Ambiguous input 'Listen' should resolve to 'Listen Labs' for later passes."""
    queries: list[str] = []

    def mock_search(query, **kwargs):
        queries.append(query)
        if "overview" in query or "leadership" in query:
            content = {**PROFILE_CONTENT, "canonical_name": "Listen Labs"}
            return _make_response(content, ["https://a.com", "https://b.com"])
        # Return good responses for all other passes
        return _make_response(FUNDING_CONTENT, ["https://c.com", "https://d.com"])

    monkeypatch.setattr("research_assistant.intelligence.run_search", mock_search)

    brief = build_brief("Listen", focus="all")

    # Brief name should use resolved canonical
    assert brief.name == "Listen Labs"
    # Every pass after profile should use "Listen Labs", not "Listen"
    post_profile = queries[1:]
    assert all("Listen Labs" in q for q in post_profile)


def test_funding_query_includes_recent_years(monkeypatch):
    captured: list[str] = []

    def mock_search(query, **kwargs):
        captured.append(query)
        return _make_response(FUNDING_CONTENT, ["https://a.com", "https://b.com"])

    monkeypatch.setattr("research_assistant.intelligence.run_search", mock_search)
    build_brief("Exa AI", focus="funding")

    assert any("2025" in q or "2026" in q for q in captured)


# ---------------------------------------------------------------------------
# Retry / thin degradation
# ---------------------------------------------------------------------------


def test_thin_result_prompts_and_retries_successfully(monkeypatch):
    call_count = 0

    def mock_search(query, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _thin_response()
        return _make_response(PROFILE_CONTENT, ["https://a.com", "https://b.com"])

    monkeypatch.setattr("research_assistant.intelligence.run_search", mock_search)
    monkeypatch.setattr("builtins.input", lambda: "Exa AI neural search startup")

    brief = build_brief("Exa", focus="profile")

    assert "profile" not in brief.thin_sections
    assert call_count == 2


def test_two_thin_results_marks_section_and_suggests_manual(monkeypatch, capsys):
    monkeypatch.setattr(
        "research_assistant.intelligence.run_search",
        lambda *a, **kw: _thin_response(),
    )
    inputs = iter(["some refined query", ""])
    monkeypatch.setattr("builtins.input", lambda: next(inputs))

    brief = build_brief("UnknownCorp XYZ", focus="profile")

    assert "profile" in brief.thin_sections
    assert "manually" in capsys.readouterr().err.lower()


def test_user_skips_retry_on_first_prompt(monkeypatch):
    call_count = 0

    def mock_search(query, **kwargs):
        nonlocal call_count
        call_count += 1
        return _thin_response()

    monkeypatch.setattr("research_assistant.intelligence.run_search", mock_search)
    monkeypatch.setattr("builtins.input", lambda: "")

    brief = build_brief("Ghost Inc", focus="profile")

    assert "profile" in brief.thin_sections
    assert call_count == 1
