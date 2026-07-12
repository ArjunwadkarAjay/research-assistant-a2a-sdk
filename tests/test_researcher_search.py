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
    assert mocked_get.call_args.kwargs["headers"]["X-Real-IP"] == "127.0.0.1"
    assert mocked_get.call_args.kwargs["headers"]["X-Forwarded-For"] == "127.0.0.1"
    assert "SearxNG result" in result
    assert "hello" in result


def test_perform_research_uses_internal_docker_service_when_running_in_container(monkeypatch):
    monkeypatch.delenv("SEARXNG_URL", raising=False)
    monkeypatch.delenv("SEARXNG_BASE_URL", raising=False)
    monkeypatch.setattr(researcher_main.os.path, "exists", lambda path: path == "/.dockerenv")

    class MockResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    with patch("apps.researcher.main.httpx.get", return_value=MockResponse({"results": [{"title": "Docker result", "content": "inside"}]})) as mocked_get:
        result = researcher_main.perform_research("python")

    mocked_get.assert_called_once()
    assert mocked_get.call_args.args[0] == "http://searxng:8080/search"
    assert "Docker result" in result
    assert "inside" in result


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


def test_perform_research_uses_structured_fallback_when_search_fails(monkeypatch):
    monkeypatch.delenv("SEARXNG_URL", raising=False)
    monkeypatch.delenv("SEARXNG_BASE_URL", raising=False)

    with patch("apps.researcher.main.httpx.get", side_effect=RuntimeError("offline")):
        result = researcher_main.perform_research("agent frameworks")

    assert "Topic:" in result
    assert "agent frameworks" in result
    assert "Potential angle" in result


def test_perform_research_returns_requested_number_of_results(monkeypatch):
    monkeypatch.delenv("SEARXNG_URL", raising=False)
    monkeypatch.delenv("SEARXNG_BASE_URL", raising=False)

    class MockResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    payload = {
        "results": [
            {"title": f"Result {i}", "content": f"Content {i}"}
            for i in range(1, 7)
        ]
    }

    with patch("apps.researcher.main.httpx.get", return_value=MockResponse(payload)):
        result = researcher_main.perform_research("python", result_count=5)

    assert result.count("- Result") == 5
    assert "Result 5" in result
    assert "Result 6" not in result
