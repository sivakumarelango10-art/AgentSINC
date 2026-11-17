from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

os.environ["AGENTSINC_DB_PATH"] = str(Path("tests") / f"test-{uuid4().hex}.sqlite3")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.db import add_event, connect, set_runtime_value  # noqa: E402


client = TestClient(app)


def test_overview_has_six_idle_office_agents_and_no_fake_tasks() -> None:
    response = client.get("/api/v1/overview")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["agents"]) == 6
    assert {agent["id"] for agent in payload["agents"]} == {
        "ceo", "team_lead", "developer", "designer", "researcher", "tester"
    }
    assert all(agent["status"] == "idle" for agent in payload["agents"])
    assert payload["tasks"] == []
    assert payload["runtime"]["memory_records"] == 0
    assert "google_search_enabled" in payload["runtime"]


def test_team_lead_cannot_receive_direct_task_outside_orchestration() -> None:
    response = client.post(
        "/api/v1/tasks",
        json={
            "agent_id": "team_lead",
            "title": "Coordinate a release review",
            "instructions": "Delegate research, design, development and QA reviews, then consolidate reports.",
        },
    )
    assert response.status_code == 409
    assert "orchestration" in response.json()["detail"].lower()


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



def test_overview_exposes_latest_local_generation_metrics() -> None:
    set_runtime_value(
        "last_generation_metrics",
        '{"model":"qwen3:4b","agent_id":"developer","task_id":"test-task",'
        '"elapsed_seconds":4.2,"prompt_tokens":900,"generated_tokens":160,'
        '"tokens_per_second":40.0,"load_seconds":0.3,"measured_at":"2026-11-16T00:00:00+00:00"}',
    )
    response = client.get("/api/v1/overview")
    assert response.status_code == 200
    metrics = response.json()["runtime"]["last_generation_metrics"]
    assert metrics["model"] == "qwen3:4b"
    assert metrics["tokens_per_second"] == 40.0
    assert metrics["generated_tokens"] == 160



def test_overview_exposes_backend_driven_team_lead_room_and_latest_activity() -> None:
    created = client.post(
        "/api/v1/orchestrations",
        json={
            "title": "Coordinate the office review",
            "instructions": "Coordinate a review of the office scene and report specialist findings.",
        },
    )
    assert created.status_code == 201
    orchestration_id = created.json()["orchestration"]["id"]

    with connect() as connection:
        connection.execute(
            "UPDATE orchestrations SET status='running', stage='executing' WHERE id=?",
            (orchestration_id,),
        )
        add_event(
            connection,
            "team_lead",
            None,
            "team_lead_location_changed",
            "Team Lead moved to the discussion room for the specialist handoff.",
            orchestration_id=orchestration_id,
        )
        connection.commit()

    overview = client.get("/api/v1/overview")
    assert overview.status_code == 200
    lead = next(item for item in overview.json()["agents"] if item["id"] == "team_lead")
    assert lead["location"] == "discussion"
    assert lead["latestActivity"] == "Team Lead moved to the discussion room for the specialist handoff."

    with connect() as connection:
        connection.execute(
            "UPDATE orchestrations SET stage='synthesizing' WHERE id=?",
            (orchestration_id,),
        )
        connection.commit()

    next_overview = client.get("/api/v1/overview").json()
    lead = next(item for item in next_overview["agents"] if item["id"] == "team_lead")
    assert lead["location"] == "meeting"



def test_agent_location_is_persisted_and_recorded_in_timeline() -> None:
    moved = client.post(
        "/api/v1/agents/developer/location",
        json={"location": "meeting"},
    )
    assert moved.status_code == 200
    assert moved.json()["location"] == "meeting"

    overview = client.get("/api/v1/overview")
    assert overview.status_code == 200
    developer = next(item for item in overview.json()["agents"] if item["id"] == "developer")
    assert developer["location"] == "meeting"
    assert "sent to the meeting" in developer["latestActivity"]

    invalid = client.post(
        "/api/v1/agents/developer/location",
        json={"location": "server-room"},
    )
    assert invalid.status_code == 422


def test_team_lead_cannot_be_manually_moved_during_active_orchestration() -> None:
    created = client.post(
        "/api/v1/orchestrations",
        json={
            "title": "Active handoff",
            "instructions": "Coordinate a short specialist handoff and consolidate the outcome.",
        },
    )
    orchestration_id = created.json()["orchestration"]["id"]
    with connect() as connection:
        connection.execute(
            "UPDATE orchestrations SET status='running', stage='executing' WHERE id=?",
            (orchestration_id,),
        )
        connection.commit()

    response = client.post(
        "/api/v1/agents/team_lead/location",
        json={"location": "desk"},
    )
    assert response.status_code == 409



def test_orchestrated_specialists_move_to_discussion_then_meeting_then_return_home() -> None:
    created = client.post(
        "/api/v1/orchestrations",
        json={
            "title": "Coordinate a specialist review",
            "instructions": "Have research, design, development and QA review the current system and share evidence.",
        },
    )
    orchestration_id = created.json()["orchestration"]["id"]
    with connect() as connection:
        now = "2026-11-17T00:00:00+00:00"
        for agent_id in ("developer", "designer", "researcher", "tester"):
            connection.execute(
                """INSERT INTO tasks
                (id, agent_id, title, instructions, status, progress, created_at, updated_at, orchestration_id)
                VALUES (?, ?, ?, ?, 'queued', 0, ?, ?, ?)""",
                (
                    f"task-{agent_id}", agent_id, f"{agent_id} review",
                    "Review the real project and return evidence-backed findings.",
                    now, now, orchestration_id,
                ),
            )
        connection.execute(
            "UPDATE orchestrations SET status='running', stage='executing' WHERE id=?",
            (orchestration_id,),
        )
        connection.commit()

    executing = client.get("/api/v1/overview").json()
    locations = {
        item["id"]: item["location"]
        for item in executing["agents"]
        if item["id"] in {"developer", "designer", "researcher", "tester"}
    }
    assert set(locations.values()) == {"discussion"}

    with connect() as connection:
        connection.execute(
            "UPDATE tasks SET status='completed', progress=100, result='Verified specialist report.' WHERE orchestration_id=?",
            (orchestration_id,),
        )
        connection.execute(
            "UPDATE orchestrations SET stage='synthesizing' WHERE id=?",
            (orchestration_id,),
        )
        connection.commit()

    synthesizing = client.get("/api/v1/overview").json()
    locations = {
        item["id"]: item["location"]
        for item in synthesizing["agents"]
        if item["id"] in {"developer", "designer", "researcher", "tester"}
    }
    assert set(locations.values()) == {"meeting"}

    with connect() as connection:
        connection.execute(
            "UPDATE orchestrations SET status='completed', stage='completed' WHERE id=?",
            (orchestration_id,),
        )
        connection.commit()

    completed = client.get("/api/v1/overview").json()
    locations = {
        item["id"]: item["location"]
        for item in completed["agents"]
        if item["id"] in {"developer", "designer", "researcher", "tester"}
    }
    assert set(locations.values()) == {"desk"}
