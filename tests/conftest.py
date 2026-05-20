import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_exa(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("research_assistant.search.Exa", lambda api_key: mock)
    return mock
