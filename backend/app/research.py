from __future__ import annotations

import os
from typing import Any

import httpx


def google_search_is_enabled() -> bool:
    enabled = os.getenv("AGENTSINC_GOOGLE_SEARCH_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    key = os.getenv("GEMINI_API_KEY", "").strip()
    return enabled and bool(key)


async def fetch_google_search_context(
    client: httpx.AsyncClient,
    mission_title: str,
    mission_instructions: str,
) -> str:
    """Fetch optional Google Search-grounded research through the Gemini API.

    This sends only the Research Agent's mission prompt to Google. It does not
    send the local workspace snapshot or SQLite memory.
    """
    if not google_search_is_enabled():
        return (
            "Google Search is not enabled. No external web results were retrieved. "
            "Do not claim that web research was performed; continue with local evidence and "
            "identify where current external verification is still needed."
        )

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("AGENTSINC_GOOGLE_SEARCH_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
    prompt = (
        "You are a research assistant using Google Search grounding. Research the following mission. "
        "Prioritize official documentation and primary sources, use current sources where relevant, "
        "distinguish facts from recommendations, and include source URLs in your response. "
        "Do not claim to inspect local files or execute actions.\n\n"
        f"MISSION: {mission_title[:160]}\n\n"
        f"RESEARCH QUESTION AND SCOPE:\n{mission_instructions[:5000]}"
    )
    response = await client.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1100},
        },
        timeout=httpx.Timeout(45.0, connect=6.0),
    )
    response.raise_for_status()
    payload: dict[str, Any] = response.json()
    candidates = payload.get("candidates") or []
    if not candidates:
        raise RuntimeError("Google Search returned no research candidate.")
    candidate = candidates[0]
    parts = (candidate.get("content") or {}).get("parts") or []
    answer = "\n".join(str(part.get("text") or "") for part in parts if part.get("text")).strip()
    grounding = candidate.get("groundingMetadata") or candidate.get("grounding_metadata") or {}
    chunks = grounding.get("groundingChunks") or grounding.get("grounding_chunks") or []
    sources: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        web = chunk.get("web") or {}
        uri = str(web.get("uri") or web.get("url") or "").strip()
        title = str(web.get("title") or uri).strip()
        if uri.startswith("https://") and uri not in seen:
            seen.add(uri)
            sources.append(f"- {title}: {uri}")
    queries = grounding.get("webSearchQueries") or grounding.get("web_search_queries") or []
    sections = ["GOOGLE SEARCH-GROUNDED RESEARCH (external source; validate against repository evidence):"]
    if queries:
        sections.append("Search queries: " + "; ".join(str(query) for query in queries[:8]))
    sections.append(answer or "Google Search returned source metadata but no readable answer text.")
    if sources:
        sections.append("Grounding sources:\n" + "\n".join(sources[:12]))
    else:
        sections.append("No grounding source URLs were supplied in the response.")
    return "\n\n".join(sections)[:9000]
