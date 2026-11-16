from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

os.environ["AGENTSINC_DB_PATH"] = str(Path("tests") / f"test-{uuid4().hex}.sqlite3")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


client = TestClient(app)


def test_overview_has_five_idle_agents_and_no_fake_tasks() -> None:
    response = client.get("/api/v1/overview")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["agents"]) == 5
    assert {agent["id"] for agent in payload["agents"]} == {
        "ceo", "developer", "designer", "researcher", "tester"
    }
    assert all(agent["status"] == "idle" for agent in payload["agents"])
    assert payload["tasks"] == []


def test_create_mission_persists_task_and_timeline_event() -> None:
    response = client.post(
        "/api/v1/tasks",
        json={
            "agent_id": "developer",
            "title": "Review the frontend architecture",
            "instructions": "Inspect the current architecture notes and prepare a structured review.",
        },
    )
    assert response.status_code == 201
    task = response.json()["task"]
    assert task["status"] == "queued"
    assert task["agent_id"] == "developer"

    overview = client.get("/api/v1/overview").json()
    assert any(item["id"] == task["id"] for item in overview["tasks"])
    assert any(
        event["task_id"] == task["id"] and event["event_type"] == "mission_queued"
        for event in overview["events"]
    )


def test_pause_prevents_new_mission_and_resume_restores_assignment() -> None:
    paused = client.post("/api/v1/agents/designer/control", json={"action": "pause"})
    assert paused.status_code == 200
    assert paused.json()["paused"] is True

    rejected = client.post(
        "/api/v1/tasks",
        json={
            "agent_id": "designer",
            "title": "Create a color direction",
            "instructions": "Prepare an alternative color direction for the office.",
        },
    )
    assert rejected.status_code == 409

    resumed = client.post("/api/v1/agents/designer/control", json={"action": "resume"})
    assert resumed.status_code == 200
    assert resumed.json()["paused"] is False


def test_queued_mission_can_be_cancelled() -> None:
    created = client.post(
        "/api/v1/tasks",
        json={
            "agent_id": "tester",
            "title": "Prepare a smoke test plan",
            "instructions": "Create a concise smoke test plan for the AgentSINC local runtime.",
        },
    )
    task_id = created.json()["task"]["id"]
    cancelled = client.post(f"/api/v1/tasks/{task_id}/cancel")
    assert cancelled.status_code == 200

    overview = client.get("/api/v1/overview").json()
    task = next(item for item in overview["tasks"] if item["id"] == task_id)
    assert task["status"] == "cancelled"


def test_missing_agent_returns_not_found() -> None:
    response = client.post(
        "/api/v1/tasks",
        json={
            "agent_id": "not-real",
            "title": "Some task",
            "instructions": "This task should not be assigned to a missing agent.",
        },
    )
    assert response.status_code == 404


def test_workspace_summary_is_available_and_read_only() -> None:
    response = client.get("/api/v1/workspace/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["read_only"] is True
    assert payload["sensitive_files_excluded"] is True


def test_workspace_api_blocks_parent_directory_traversal() -> None:
    response = client.get("/api/v1/workspace/read", params={"path": "../outside.txt"})
    assert response.status_code == 400


def test_workspace_api_can_search_real_repository_files() -> None:
    response = client.get(
        "/api/v1/workspace/search",
        params={"q": "Ollama local worker", "limit": 5},
    )
    assert response.status_code == 200
    paths = [item["path"] for item in response.json()["results"]]
    assert "backend/app/worker.py" in paths


def test_ceo_orchestration_is_persisted_and_visible_in_overview() -> None:
    response = client.post(
        "/api/v1/orchestrations",
        json={
            "title": "Prepare the next AgentSINC release plan",
            "instructions": "Review the current repository and coordinate specialists to recommend the safest next release milestones.",
        },
    )
    assert response.status_code == 201
    orchestration = response.json()["orchestration"]
    assert orchestration["status"] == "queued"
    assert orchestration["stage"] == "planning"
    assert orchestration["plan"] is None

    detail = client.get(f"/api/v1/orchestrations/{orchestration['id']}")
    assert detail.status_code == 200
    assert detail.json()["orchestration"]["tasks"] == []

    overview = client.get("/api/v1/overview").json()
    assert any(item["id"] == orchestration["id"] for item in overview["orchestrations"])


def test_queued_ceo_orchestration_can_be_cancelled() -> None:
    created = client.post(
        "/api/v1/orchestrations",
        json={
            "title": "Create a short design research plan",
            "instructions": "Coordinate specialist analysis of the current design and propose a short improvement plan.",
        },
    )
    orchestration_id = created.json()["orchestration"]["id"]
    cancelled = client.post(f"/api/v1/orchestrations/{orchestration_id}/cancel")
    assert cancelled.status_code == 200

    detail = client.get(f"/api/v1/orchestrations/{orchestration_id}").json()["orchestration"]
    assert detail["status"] == "cancelled"
    assert detail["stage"] == "cancelled"


def test_unknown_ceo_orchestration_returns_not_found() -> None:
    response = client.get("/api/v1/orchestrations/not-a-real-id")
    assert response.status_code == 404
