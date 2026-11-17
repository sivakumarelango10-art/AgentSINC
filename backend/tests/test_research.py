from __future__ import annotations

import asyncio
import json

import httpx

from app.research import fetch_google_search_context, google_search_is_enabled
from app.redaction import redact_secrets


def test_google_search_requires_explicit_opt_in_and_api_key(monkeypatch) -> None:
    monkeypatch.setenv("AGENTSINC_GOOGLE_SEARCH_ENABLED", "true")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert google_search_is_enabled() is False

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("AGENTSINC_GOOGLE_SEARCH_ENABLED", "false")
    assert google_search_is_enabled() is False


def test_google_research_calls_grounded_search_and_returns_source_urls(monkeypatch) -> None:
    monkeypatch.setenv("AGENTSINC_GOOGLE_SEARCH_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("AGENTSINC_GOOGLE_SEARCH_MODEL", "gemini-2.5-flash")
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "candidates": [{
                    "content": {"parts": [{"text": "Official documentation confirms the API behavior."}]},
                    "groundingMetadata": {
                        "webSearchQueries": ["official API documentation"],
                        "groundingChunks": [{
                            "web": {
                                "uri": "https://developers.google.com/example",
                                "title": "Official documentation",
                            }
                        }],
                    },
                }]
            },
        )

    async def run() -> str:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await fetch_google_search_context(
                client,
                "Research current API guidance",
                "Find current official API documentation and cite sources.",
            )

    result = asyncio.run(run())
    payload = captured["payload"]
    assert str(captured["url"]).endswith("/gemini-2.5-flash:generateContent")
    assert captured["headers"]["x-goog-api-key"] == "test-key"
    assert payload["tools"] == [{"google_search": {}}]
    assert "Find current official API documentation" in payload["contents"][0]["parts"][0]["text"]
    assert "Official documentation confirms" in result
    assert "https://developers.google.com/example" in result


def test_google_search_disabled_returns_honest_no_research_message(monkeypatch) -> None:
    monkeypatch.setenv("AGENTSINC_GOOGLE_SEARCH_ENABLED", "false")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    async def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("Disabled Google research must not make a network request.")

    async def run() -> str:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await fetch_google_search_context(client, "Research", "Find official documentation.")

    result = asyncio.run(run())
    assert "not enabled" in result.lower()
    assert "No external web results were retrieved" in result



def test_secret_redaction_consumes_complete_authorization_values() -> None:
    source = (
        "api_key=private-api-key-value "
        "Authorization=Bearer private-bearer-token-value "
        "Authorization: Basic private-basic-token-value "
        "Bearer private-standalone-token-value"
    )
    cleaned = redact_secrets(source)

    assert "private-api-key-value" not in cleaned
    assert "private-bearer-token-value" not in cleaned
    assert "private-basic-token-value" not in cleaned
    assert "private-standalone-token-value" not in cleaned
    assert cleaned.count("[REDACTED]") >= 4
