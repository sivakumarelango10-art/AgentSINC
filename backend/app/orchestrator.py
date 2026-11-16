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


def _validate_plan(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary")
    items = payload.get("tasks")
    if not isinstance(summary, str) or not summary.strip():
        raise RuntimeError("CEO plan is missing a summary.")
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_SPECIALIST_TASKS:
        raise RuntimeError(f"CEO must delegate between 1 and {MAX_SPECIALIST_TASKS} specialist missions.")
    tasks: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            raise RuntimeError("Every delegated mission must be a JSON object.")
        agent_id, title, instructions = item.get("agent_id"), item.get("title"), item.get("instructions")
        if agent_id not in SPECIALIST_IDS:
            raise RuntimeError("CEO may delegate only to Developer, Designer, Researcher or Tester.")
        if not isinstance(title, str) or not 3 <= len(title.strip()) <= 120:
            raise RuntimeError("A delegated mission title is invalid.")
        if not isinstance(instructions, str) or not 20 <= len(instructions.strip()) <= 12000:
            raise RuntimeError("A delegated mission needs valid instructions.")
        tasks.append({"agent_id": agent_id, "title": title.strip(), "instructions": instructions.strip()})
    return {"summary": summary.strip()[:2000], "tasks": tasks}


def _claim_planning() -> dict[str, Any] | None:
    with connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT * FROM orchestrations WHERE status='queued' AND stage='planning' ORDER BY created_at ASC LIMIT 1"
        ).fetchone()
        if not row:
            connection.commit()
            return None
        now = utc_now()
        connection.execute(
            "UPDATE orchestrations SET status='running', started_at=?, updated_at=? WHERE id=? AND status='queued'",
            (now, now, row["id"]),
        )
        add_event(
            connection, "ceo", None, "orchestration_planning",
            f'CEO is planning: "{row["title"]}".',
            orchestration_id=row["id"],
        )
        result = dict(connection.execute("SELECT * FROM orchestrations WHERE id=?", (row["id"],)).fetchone())
        connection.commit()
        return result


def _fail(orchestration_id: str, message: str) -> None:
    now = utc_now()
    safe_message = message[:1200]
    with connect() as connection:
        connection.execute(
            "UPDATE orchestrations SET status='failed', stage='failed', error=?, updated_at=?, completed_at=? WHERE id=?",
            (safe_message, now, now, orchestration_id),
        )
        add_event(
            connection, "ceo", None, "orchestration_failed",
            f"CEO orchestration failed: {safe_message[:240]}",
            orchestration_id=orchestration_id,
        )
        connection.commit()


def _cancel(orchestration_id: str, message: str) -> None:
    now = utc_now()
    with connect() as connection:
        connection.execute(
            "UPDATE orchestrations SET status='cancelled', stage='cancelled', error=?, updated_at=?, completed_at=? WHERE id=?",
            (message[:500], now, now, orchestration_id),
        )
        add_event(
            connection, "ceo", None, "orchestration_cancelled", message,
            orchestration_id=orchestration_id,
        )
        connection.commit()


def recover_orchestrations() -> None:
    now = utc_now()
    with connect() as connection:
        connection.execute(
            "UPDATE orchestrations SET status='queued', stage='planning', updated_at=? WHERE status='running' AND stage='planning'",
            (now,),
        )
        connection.execute(
            "UPDATE orchestrations SET stage='executing', updated_at=? WHERE status='running' AND stage='synthesizing'",
            (now,),
        )
        connection.commit()
