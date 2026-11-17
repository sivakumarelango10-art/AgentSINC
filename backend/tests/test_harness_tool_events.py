from __future__ import annotations

import asyncio
import json

import httpx

from app.db import connect, create_task, init_db
from app.harness import AgentHarness


def _task() -> dict:
    return create_task(
        "developer",
        "Inspect the current repository",
        "Search the source tree and report concrete evidence.",
    )


def test_harness_persists_started_and_completed_repository_search_events(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTSINC_DB_PATH", str(tmp_path / "tool-events.sqlite3"))
    init_db()
    task = _task()
    monkeypatch.setattr(
        "app.harness.search_workspace",
        lambda query, limit: [{"path": "frontend/src/app/page.tsx", "line": 12, "snippet": "AgentSINC"}],
    )

    async def run_tool() -> str:
        async with httpx.AsyncClient() as client:
            harness = AgentHarness(task, client, progress=lambda *_: None, cancelled=lambda: False)
            return await harness.execute_tool("repo.search", {"query": "AgentSINC", "limit": 4})

    result = asyncio.run(run_tool())
    assert "frontend/src/app/page.tsx" in result

    with connect() as connection:
        events = connection.execute(
            "SELECT event_type, message FROM events WHERE task_id=? ORDER BY id",
            (task["id"],),
        ).fetchall()

    assert [row["event_type"] for row in events] == ["tool_started", "tool_completed"]
    assert "repo.search" in events[0]["message"]
    assert "1 match" in events[1]["message"]
    assert "frontend/src/app/page.tsx" in events[1]["message"]


def test_harness_persists_real_test_suite_status_and_exit_code(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTSINC_DB_PATH", str(tmp_path / "tool-tests.sqlite3"))
    init_db()
    task = _task()
    monkeypatch.setattr(
        "app.harness.run_test_suite",
        lambda suite: {
            "status": "passed",
            "suite": suite,
            "exit_code": 0,
            "stdout": "12 passed in 0.42s",
            "stderr": "",
        },
    )

    async def run_tool() -> str:
        async with httpx.AsyncClient() as client:
            harness = AgentHarness(task, client, progress=lambda *_: None, cancelled=lambda: False)
            return await harness.execute_tool("tests.run", {"suite": "python-tests"})

    result = json.loads(asyncio.run(run_tool()))
    assert result["status"] == "passed"

    with connect() as connection:
        event = connection.execute(
            "SELECT event_type, message FROM events WHERE task_id=? ORDER BY id DESC LIMIT 1",
            (task["id"],),
        ).fetchone()

    assert event["event_type"] == "tool_completed"
    assert "python-tests: PASSED" in event["message"]
    assert "exit=0" in event["message"]
    assert "12 passed" in event["message"]
