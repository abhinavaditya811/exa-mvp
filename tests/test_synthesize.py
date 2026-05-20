from unittest.mock import MagicMock

from research_assistant.synthesize import extract


def _make_response(answer: str, urls: list[str]) -> MagicMock:
    response = MagicMock()
    response.output.content = answer
    cites = [MagicMock(url=u, title=f"Title {i}") for i, u in enumerate(urls, start=1)]
    response.output.grounding = [MagicMock(citations=cites)]
    return response


def test_extracts_answer_and_citations():
    result = extract(_make_response("Python is a language.", ["https://python.org"]))

    assert result.answer == "Python is a language."
    assert len(result.citations) == 1
    assert result.citations[0].url == "https://python.org"
    assert result.citations[0].index == 1


def test_multiple_citations_numbered_sequentially():
    result = extract(_make_response("answer", ["https://a.com", "https://b.com"]))

    assert [c.index for c in result.citations] == [1, 2]


def test_no_output_returns_empty():
    response = MagicMock()
    response.output = None
    result = extract(response)

    assert result.answer == ""
    assert result.citations == []


def test_empty_grounding_returns_no_citations():
    response = MagicMock()
    response.output.content = "answer"
    response.output.grounding = []
    result = extract(response)

    assert result.citations == []
