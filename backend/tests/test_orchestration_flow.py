from __future__ import annotations

import asyncio
import json

import httpx

from app.db import connect, create_orchestration, get_orchestration_detail, init_db
from app.orchestrator import _claim_planning, _claim_synthesis, _plan, _synthesize


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
    seen_formats: list[str | None] = []

    async def handler(http_request: httpx.Request) -> httpx.Response:
        payload = json.loads(http_request.content)
        seen_formats.append(payload.get("format"))
        if payload.get("format") == "json":
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
    assert seen_formats == ["json", None]
