import pytest
from unittest.mock import MagicMock, call

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
    """Well-formed response with content dict and enough citations."""
    response = MagicMock()
    response.output.content = content
    cites = [MagicMock(url=u, title=f"Title") for u in urls]
    response.output.grounding = [MagicMock(citations=cites)]
    return response


def _thin_response() -> MagicMock:
    """Response with zero citations — triggers thin detection."""
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
        MagicMock(citations=[cite]),  # duplicate
    ]
    cites = _get_citations(r)
    assert len(cites) == 1
    assert cites[0] == ("https://a.com", "A")


# ---------------------------------------------------------------------------
# Integration: build_brief happy path
# ---------------------------------------------------------------------------


PROFILE_CONTENT = {
    "overview": "Neural search API.",
    "founded_year": "2022",
    "headquarters": "San Francisco",
    "employee_count": "~50",
    "ceo": "Jeff Wang",
    "cto": None,
    "key_products": "Search API",
}

FUNDING_CONTENT = {
    "latest_round": "Series A",
    "latest_amount": "$17M",
    "latest_date": "Feb 2024",
    "total_raised": "$22M",
    "key_investors": ["a16z"],
    "valuation": None,
}

NEWS_CONTENT = {
    "headlines": ["Launched deep-reasoning search"],
    "product_launches": [],
}

COMPETITORS_CONTENT = {
    "direct_competitors": ["Perplexity", "Tavily"],
    "competitive_landscape": "Competitive AI search space.",
}


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
        return _make_response({}, [])

    monkeypatch.setattr("research_assistant.intelligence.run_search", mock_search)

    brief = build_brief("Exa AI", focus="all")

    assert len(calls) == 4
    assert brief.profile is not None
    assert brief.profile.ceo == "Jeff Wang"
    assert brief.funding is not None
    assert brief.funding.latest_round == "Series A"
    assert brief.news is not None
    assert brief.news.headlines == ["Launched deep-reasoning search"]
    assert brief.competitors == ["Perplexity", "Tavily"]
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
    # First retry: provide query; second retry: skip (empty input)
    inputs = iter(["some refined query", ""])
    monkeypatch.setattr("builtins.input", lambda: next(inputs))

    brief = build_brief("UnknownCorp XYZ", focus="profile")

    assert "profile" in brief.thin_sections
    stderr = capsys.readouterr().err
    assert "manually" in stderr.lower()


def test_user_skips_retry_on_first_prompt(monkeypatch):
    call_count = 0

    def mock_search(query, **kwargs):
        nonlocal call_count
        call_count += 1
        return _thin_response()

    monkeypatch.setattr("research_assistant.intelligence.run_search", mock_search)
    monkeypatch.setattr("builtins.input", lambda: "")  # user presses Enter immediately

    brief = build_brief("Ghost Inc", focus="profile")

    assert "profile" in brief.thin_sections
    assert call_count == 1  # no retry after empty input
