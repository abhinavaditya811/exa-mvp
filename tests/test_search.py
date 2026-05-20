import pytest
from unittest.mock import MagicMock

from research_assistant.search import run_search, OUTPUT_SCHEMA


def test_default_params(mock_exa, monkeypatch):
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    mock_exa.search.return_value = MagicMock()

    run_search("what is Python?")

    mock_exa.search.assert_called_once_with(
        "what is Python?",
        type="deep",
        num_results=10,
        contents={"highlights": True},
        output_schema=OUTPUT_SCHEMA,
    )


def test_full_text_adds_text_contents(mock_exa, monkeypatch):
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    mock_exa.search.return_value = MagicMock()

    run_search("query", full_text=True)

    contents = mock_exa.search.call_args[1]["contents"]
    assert "text" in contents
    assert contents["text"]["max_characters"] == 5000


def test_custom_type_and_num_results(mock_exa, monkeypatch):
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    mock_exa.search.return_value = MagicMock()

    run_search("query", num_results=5, search_type="deep-reasoning")

    call = mock_exa.search.call_args[1]
    assert call["num_results"] == 5
    assert call["type"] == "deep-reasoning"


def test_missing_api_key_exits(mock_exa, monkeypatch):
    monkeypatch.delenv("EXA_API_KEY", raising=False)

    with pytest.raises(SystemExit):
        run_search("query")
