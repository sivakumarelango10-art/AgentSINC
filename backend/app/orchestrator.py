from __future__ import annotations

import json
from typing import Any

import httpx

from .db import add_event, connect, utc_now
from .workspace import WorkspaceError, build_workspace_context

SPECIALIST_IDS = ("developer", "designer", "researcher", "tester")
MAX_SPECIALIST_TASKS = 4


def orchestration_cancelled(orchestration_id: str) -> bool:
    with connect() as connection:
        row = connection.execute(
            "SELECT cancel_requested FROM orchestrations WHERE id=?",
            (orchestration_id,),
        ).fetchone()
    return bool(row and row["cancel_requested"])


def task_cancelled(task_id: str) -> bool:
    with connect() as connection:
        row = connection.execute(
            """SELECT t.cancel_requested, o.cancel_requested AS parent_cancelled
            FROM tasks t LEFT JOIN orchestrations o ON o.id=t.orchestration_id
            WHERE t.id=?""",
            (task_id,),
        ).fetchone()
    return bool(row and (row["cancel_requested"] or row["parent_cancelled"]))


async def _chat(
    client: httpx.AsyncClient,
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    timeout_seconds: float,
    json_mode: bool = False,
) -> str:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "keep_alive": "10m",
        "options": {"temperature": 0.18},
    }
    if json_mode:
        payload["format"] = "json"
    response = await client.post(
        f"{base_url}/api/chat",
        json=payload,
        timeout=httpx.Timeout(timeout_seconds, connect=5.0),
    )
    response.raise_for_status()
    content = response.json().get("message", {}).get("content", "")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Ollama returned an empty orchestration response.")
    return content.strip()


def _json_object(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith(""):
        cleaned = cleaned.split("\n", 1)[-1]
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise RuntimeError("CEO plan did not contain a JSON object.")
        try:
            value = json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError as exc:
            raise RuntimeError("CEO plan contained invalid JSON.") from exc
    if not isinstance(value, dict):
        raise RuntimeError("CEO plan must be a JSON object.")
    return value
