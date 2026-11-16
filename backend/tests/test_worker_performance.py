from __future__ import annotations

import asyncio
import json

import httpx

from app.db import connect, create_task, get_runtime_value, init_db
from app import worker


def test_specialist_request_uses_local_performance_limits_and_records_metrics(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTSINC_DB_PATH", str(tmp_path / "worker-performance.sqlite3"))
    init_db()
    task = create_task(
        "developer",
        "Review API implementation",
        "Inspect the local API source and report the most important implementation risks.",
    )
    task.update({
        "agent_name": "Dev Agent",
        "agent_role": "Developer",
        "agent_department": "Development Studio",
        "agent_model_profile": "Code Specialist",
    })
    with connect() as connection:
        connection.execute("UPDATE tasks SET status='running' WHERE id=?", (task["id"],))
        connection.commit()

    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        lines = [
            {
                "message": {"content": "Evidence-backed API review."},
                "done": False,
            },
            {
                "message": {"content": ""},
                "done": True,
                "total_duration": 3_000_000_000,
                "load_duration": 500_000_000,
                "prompt_eval_count": 1200,
                "prompt_eval_duration": 1_000_000_000,
                "eval_count": 80,
                "eval_duration": 2_000_000_000,
            },
        ]
        body = "".join(json.dumps(item) + "\n" for item in lines)
        return httpx.Response(200, content=body.encode(), headers={"content-type": "application/x-ndjson"})

    monkeypatch.setattr(worker, "build_workspace_context", lambda query: type(
        "Workspace", (), {"text": "### FILE: backend/app/main.py\nRead-only test source.", "files": ["backend/app/main.py"]}
    )())
    monkeypatch.setattr(worker, "_cancel_requested", lambda task_id: False)

    async def run() -> str:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await worker._run_ollama_task(client, task, "qwen3:4b")

    result = asyncio.run(run())

    assert result == "Evidence-backed API review."
    assert captured["keep_alive"] == "20m"
    assert captured["think"] is False
    options = captured["options"]
    assert options["num_ctx"] == 4096
    assert options["num_predict"] == 650
    assert options["temperature"] == 0.2

    metrics = json.loads(get_runtime_value("last_generation_metrics") or "{}")
    assert metrics["model"] == "qwen3:4b"
    assert metrics["agent_id"] == "developer"
    assert metrics["prompt_tokens"] == 1200
    assert metrics["generated_tokens"] == 80
    assert metrics["tokens_per_second"] == 40.0
    assert metrics["load_seconds"] == 0.5
