from __future__ import annotations

import asyncio
import json

import httpx

from app.db import connect, create_orchestration, get_orchestration_detail, init_db
from app.orchestrator import CEO_PLAN_SCHEMA, _claim_planning, _claim_synthesis, _plan, _synthesize, _validate_plan


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
        "CEO delegated specialist missions: Review backend API; "
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
