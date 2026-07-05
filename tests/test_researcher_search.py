from unittest.mock import patch

from apps.researcher import main as researcher_main


def test_perform_research_uses_searxng_when_configured(monkeypatch):
    monkeypatch.setenv("SEARXNG_URL", "http://searxng:8080")

    class MockResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    with patch("apps.researcher.main.httpx.get", return_value=MockResponse({"results": [{"title": "SearxNG result", "content": "hello"}]})) as mocked_get:
        result = researcher_main.perform_research("python")

    mocked_get.assert_called_once()
    assert "SearxNG result" in result
    assert "hello" in result


def test_perform_research_uses_localhost_fallback_when_not_configured(monkeypatch):
    monkeypatch.delenv("SEARXNG_URL", raising=False)
    monkeypatch.delenv("SEARXNG_BASE_URL", raising=False)

    class MockResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    with patch("apps.researcher.main.httpx.get", return_value=MockResponse({"results": [{"title": "Fallback result", "content": "world"}]})) as mocked_get:
        result = researcher_main.perform_research("python")

    mocked_get.assert_called_once()
    assert mocked_get.call_args.args[0] == "http://localhost:8888/search"
    assert "Fallback result" in result
    assert "world" in result
