from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import httpx

from app.db import connect, create_orchestration, get_orchestration_detail, init_db
from app import orchestrator
from app.orchestrator import CEO_PLAN_SCHEMA, _claim_planning, _claim_synthesis, _explicit_specialist_plan, _plan, _strip_internal_thinking, _synthesize, _validate_plan


def test_ceo_plans_delegates_and_synthesizes_with_mock_ollama(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTSINC_DB_PATH", str(tmp_path / "orchestration-test.sqlite3"))
    init_db()
    request = create_orchestration(
        "Prepare a release readiness review",
        "Inspect the current project and coordinate specialists to prepare a release readiness report.",
    )
    generated_plan = {
        "summary": "Research the implementation and prepare a validation review.",
        "tasks": [
            {
                "agent_id": "researcher",
                "title": "Review release architecture",
                "instructions": "Inspect the project architecture and provide evidence-backed findings and risks.",
            },
            {
                "agent_id": "tester",
                "title": "Prepare release validation checklist",
                "instructions": "Review the architecture and produce a practical release validation checklist.",
            },
        ],
    }
    seen_formats: list[object] = []
    seen_think_values: list[object] = []
    seen_payloads: list[dict[str, object]] = []

    async def handler(http_request: httpx.Request) -> httpx.Response:
        payload = json.loads(http_request.content)
        seen_formats.append(payload.get("format"))
        seen_think_values.append(payload.get("think"))
        seen_payloads.append(payload)
        if isinstance(payload.get("format"), dict):
            answer = json.dumps(generated_plan)
        else:
            answer = "CEO consolidated release readiness report."
        line = json.dumps({"message": {"content": answer}, "done": True}) + "\n"
        return httpx.Response(
            200,
            content=line.encode("utf-8"),
            headers={"content-type": "application/x-ndjson"},
        )

    async def run_cycle() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            claimed = _claim_planning()
            assert claimed is not None
            assert claimed["id"] == request["id"]

            await _plan(client, "http://ollama.test", 10, "qwen3:4b", claimed)

            detail = get_orchestration_detail(request["id"])
            assert detail is not None
            assert detail["status"] == "running"
            assert detail["stage"] == "executing"
            assert len(detail["tasks"]) == 2

            now = "2026-01-01T00:00:00+00:00"
            with connect() as connection:
                connection.execute(
                    """UPDATE tasks SET status='completed', progress=100,
                    result='Specialist evidence-backed report.', updated_at=?, completed_at=?""",
                    (now, now),
                )
                connection.commit()

            ready = _claim_synthesis()
            assert ready is not None
            assert ready["id"] == request["id"]
            assert len(ready["children"]) == 2

            await _synthesize(client, "http://ollama.test", 10, "qwen3:4b", ready)

    asyncio.run(run_cycle())

    final = get_orchestration_detail(request["id"])
    assert final is not None
    assert final["status"] == "completed"
    assert final["stage"] == "completed"
    assert final["result"] == "CEO consolidated release readiness report."
    assert seen_formats == [CEO_PLAN_SCHEMA, None]
    assert seen_think_values == [False, False]
    assert [payload["keep_alive"] for payload in seen_payloads] == ["20m", "20m"]
    assert [payload["options"]["num_ctx"] for payload in seen_payloads] == [4096, 4096]
    assert [payload["options"]["num_predict"] for payload in seen_payloads] == [850, 900]


def test_qwen_plan_without_summary_derives_one_from_validated_tasks() -> None:
    plan = _validate_plan(
        {
            "tasks": [
                {
                    "agent_id": "developer",
                    "title": "Review backend API",
                    "instructions": "Inspect the backend API source files and report implementation risks.",
                },
                {
                    "agent_id": "tester",
                    "title": "Prepare runtime test checklist",
                    "instructions": "Inspect tests and prepare a clear runtime validation checklist.",
                },
            ]
        }
    )

    assert plan["summary"] == (
        "Team Lead delegated specialist missions: Review backend API; "
        "Prepare runtime test checklist"
    )
    assert len(plan["tasks"]) == 2


def test_qwen_plan_accepts_supported_summary_and_task_aliases() -> None:
    plan = _validate_plan(
        {
            "plan_summary": "Review the source and verify quality.",
            "specialist_tasks": [
                {
                    "agent_id": "researcher",
                    "title": "Review system documentation",
                    "instructions": "Inspect actual documentation and identify operational requirements.",
                }
            ],
        }
    )

    assert plan["summary"] == "Review the source and verify quality."
    assert plan["tasks"][0]["agent_id"] == "researcher"


def test_ceo_plan_still_rejects_empty_or_invalid_delegations() -> None:
    try:
        _validate_plan({"summary": "No work is planned.", "tasks": []})
    except RuntimeError as exc:
        assert "specialist missions" in str(exc)
    else:
        raise AssertionError("An empty specialist plan must be rejected.")



def test_explicit_founder_specialist_sections_are_preserved_without_llm_replanning(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTSINC_DB_PATH", str(tmp_path / "explicit-specialists.sqlite3"))
    init_db()
    instructions = """Coordinate all four specialist agents for a production-readiness audit.

1. **DEVELOPER AGENT**
Review backend architecture, FastAPI endpoints, SQLite persistence, Ollama worker and task lifecycle.

2. **DESIGNER AGENT**
Review the Next.js frontend, 3D office, agent interactions and responsive user experience.

3. **RESEARCH AGENT**
Review project documentation, architecture decisions, dependencies and production requirements.

4. **QA AGENT**
Review automated tests, error handling, runtime reliability, security boundaries and missing test coverage.
"""
    request = create_orchestration("AgentSINC Production Readiness Audit", instructions)

    plan = _explicit_specialist_plan(request)
    assert plan is not None
    assert [task["agent_id"] for task in plan["tasks"]] == [
        "developer", "designer", "researcher", "tester"
    ]
    assert "FastAPI endpoints" in plan["tasks"][0]["instructions"]
    assert "3D office" in plan["tasks"][1]["instructions"]
    assert "production requirements" in plan["tasks"][2]["instructions"]
    assert "security boundaries" in plan["tasks"][3]["instructions"]

    def no_workspace_planner_call(_query: str):
        raise AssertionError("Explicit assignments must not be reinterpreted by the model planner.")

    monkeypatch.setattr(orchestrator, "build_workspace_context", no_workspace_planner_call)

    async def handler(_http_request: httpx.Request) -> httpx.Response:
        raise AssertionError("The explicit assignment path must not call Ollama to choose specialists.")

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            claimed = _claim_planning()
            assert claimed is not None
            await _plan(client, "http://ollama.test", 10, "qwen3:4b", claimed)

    asyncio.run(run())

    detail = get_orchestration_detail(request["id"])
    assert detail is not None
    assert detail["status"] == "running"
    assert detail["stage"] == "executing"
    assert [task["agent_id"] for task in detail["tasks"]] == [
        "developer", "designer", "researcher", "tester"
    ]
    assert all(task["status"] == "queued" for task in detail["tasks"])



def test_ceo_output_removes_think_blocks() -> None:
    content = (
        "## Final report\nUseful summary.\n"
        "<think>private internal reasoning that must not be shown</think>\n"
        "## Recommendations\nKeep backups."
    )
    cleaned = _strip_internal_thinking(content)
    assert "private internal reasoning" not in cleaned
    assert "<think>" not in cleaned
    assert "Useful summary." in cleaned
    assert "Keep backups." in cleaned


def test_ceo_output_drops_unterminated_think_block() -> None:
    cleaned = _strip_internal_thinking("Final answer\n<think>unfinished hidden reasoning")
    assert cleaned == "Final answer"



def test_ceo_synthesis_is_told_about_explicitly_requested_but_missing_specialist(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTSINC_DB_PATH", str(tmp_path / "synthesis-missing-role.sqlite3"))
    init_db()
    instructions = """Coordinate all four specialists for the production-readiness audit.
1. DEVELOPER AGENT
Review backend architecture, API and task lifecycle.
2. DESIGNER AGENT
Review the frontend and 3D office experience.
3. RESEARCH AGENT
Review documentation, dependencies and hosting constraints.
4. QA AGENT
Review tests, reliability and security boundaries.
"""
    parent = create_orchestration("Production readiness audit", instructions)
    for agent_id in ("developer", "designer", "tester"):
        with connect() as connection:
            task_id = str(uuid4())
            now = "2026-11-16T00:00:00+00:00"
            title = f"{agent_id} audit report"
            connection.execute(
                """INSERT INTO tasks
                (id, agent_id, title, instructions, status, progress, created_at, updated_at,
                 started_at, completed_at, result, orchestration_id)
                VALUES (?, ?, ?, ?, 'completed', 100, ?, ?, ?, ?, ?, ?)""",
                (task_id, agent_id, title, "Review assigned area and cite actual files.",
                 now, now, now, now, f"Verified {agent_id} report with backend/app/main.py evidence.", parent["id"]),
            )
            connection.commit()
    with connect() as connection:
        connection.execute(
            "UPDATE orchestrations SET status='running', stage='executing' WHERE id=?",
            (parent["id"],),
        )
        connection.commit()

    captured: dict[str, str] = {}

    async def handler(http_request: httpx.Request) -> httpx.Response:
        payload = json.loads(http_request.content)
        captured["user"] = payload["messages"][1]["content"]
        line = json.dumps({
            "message": {"content": "## Final audit\nCompleted three reviews.\n<think>do not expose</think>"},
            "done": True,
        }) + "\n"
        return httpx.Response(200, content=line.encode(), headers={"content-type": "application/x-ndjson"})

    async def run() -> None:
        request = _claim_synthesis()
        assert request is not None
        assert request["id"] == parent["id"]
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await _synthesize(client, "http://ollama.test", 10, "qwen3:4b", request)

    asyncio.run(run())
    final = get_orchestration_detail(parent["id"])
    assert final is not None
    assert final["status"] == "completed"
    assert 'MISSING REQUESTED SPECIALISTS: ["researcher"]' in captured["user"]
    assert "do not expose" not in final["result"]
    assert "Completed three reviews." in final["result"]
