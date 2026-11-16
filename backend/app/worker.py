from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import httpx

from .db import add_event, connect, get_runtime_value, set_runtime_value, utc_now


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
POLL_SECONDS = float(os.getenv("AGENTSINC_WORKER_POLL_SECONDS", "2"))
MODEL_TIMEOUT = float(os.getenv("AGENTSINC_MODEL_TIMEOUT_SECONDS", "900"))
class MissionCancelled(Exception):
    """Raised when a founder cancels a running local model response."""


SYSTEM_POLICY = (
    "You are an AI specialist working inside AgentSINC, a local-first AI company workspace. "
    "Work only on the mission supplied by the founder. You have no shell, browser, network-search, "
    "filesystem, repository-write, deployment, email, payment, or external-action tools in this runtime. "
    "Do not claim to have changed files, run tests, searched the web, deployed software, or performed "
    "any side effect. Produce a useful, structured answer, plan, analysis, test checklist, or code proposal. "
    "Clearly state assumptions, missing information, risks, and what a human or later approved tool must do. "
    "Never invent evidence or claim completion of work you could not perform."
)


def _heartbeat(state: str = "running") -> None:
    set_runtime_value("worker_state", state)
    set_runtime_value("worker_heartbeat", utc_now())


def _ollama_model_names(payload: dict[str, Any]) -> list[str]:
    return sorted(str(item.get("name")) for item in payload.get("models", []) if item.get("name"))


async def _get_models(client: httpx.AsyncClient) -> list[str]:
    response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
    response.raise_for_status()
    return _ollama_model_names(response.json())


def _choose_model(models: list[str]) -> str | None:
    configured = get_runtime_value("selected_model") or os.getenv("AGENTSINC_OLLAMA_MODEL")
    if configured and configured in models:
        return configured
    preferred = next(
        (name for name in models if any(part in name.lower() for part in ("qwen", "llama", "mistral", "gemma"))),
        None,
    )
    selected = preferred or (models[0] if models else None)
    if selected:
        set_runtime_value("selected_model", selected)
    return selected


def _claim_next_task() -> dict[str, Any] | None:
    with connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """SELECT t.*, a.name AS agent_name, a.role AS agent_role, a.department AS agent_department,
            a.is_paused AS agent_paused, a.model_profile AS agent_model_profile
            FROM tasks t JOIN agents a ON a.id=t.agent_id
            WHERE t.status='queued' AND a.is_paused=0
            ORDER BY t.created_at ASC LIMIT 1"""
        ).fetchone()
        if not row:
            connection.commit()
            return None
        now = utc_now()
        connection.execute(
            "UPDATE tasks SET status='running', progress=5, started_at=?, updated_at=? WHERE id=? AND status='queued'",
            (now, now, row["id"]),
        )
        connection.execute(
            "UPDATE agents SET status='working', current_task_id=?, updated_at=? WHERE id=?",
            (row["id"], now, row["agent_id"]),
        )
        add_event(connection, row["agent_id"], row["id"], "mission_started",
                  f'{row["agent_name"]} started: "{row["title"]}".')
        claimed = connection.execute(
            """SELECT t.*, a.name AS agent_name, a.role AS agent_role, a.department AS agent_department,
            a.is_paused AS agent_paused, a.model_profile AS agent_model_profile
            FROM tasks t JOIN agents a ON a.id=t.agent_id WHERE t.id=?""",
            (row["id"],),
        ).fetchone()
        connection.commit()
        return dict(claimed)


def _cancel_requested(task_id: str) -> bool:
    with connect() as connection:
        row = connection.execute("SELECT cancel_requested FROM tasks WHERE id=?", (task_id,)).fetchone()
    return bool(row and row["cancel_requested"])


def _record_progress(task: dict[str, Any], progress: int, note: str | None = None) -> None:
    now = utc_now()
    with connect() as connection:
        connection.execute(
            "UPDATE tasks SET progress=?, updated_at=? WHERE id=? AND status='running'",
            (max(5, min(progress, 95)), now, task["id"]),
        )
        if note:
            add_event(connection, task["agent_id"], task["id"], "agent_progress", note)
        connection.commit()


def _finish_task(task: dict[str, Any], result: str) -> None:
    now = utc_now()
    with connect() as connection:
        connection.execute(
            """UPDATE tasks SET status='completed', progress=100, result=?, error=NULL,
            updated_at=?, completed_at=? WHERE id=?""",
            (result, now, now, task["id"]),
        )
        connection.execute(
            """UPDATE agents SET current_task_id=NULL,
            status=CASE WHEN is_paused=1 THEN 'paused' ELSE 'idle' END, updated_at=?
            WHERE id=? AND current_task_id=?""",
            (now, task["agent_id"], task["id"]),
        )
        add_event(connection, task["agent_id"], task["id"], "mission_completed",
                  f'{task["agent_name"]} completed the response for "{task["title"]}".')
        connection.commit()


def _cancel_task(task: dict[str, Any], message: str = "Mission cancelled.") -> None:
    now = utc_now()
    with connect() as connection:
        connection.execute(
            """UPDATE tasks SET status='cancelled', error=?, updated_at=?, completed_at=? WHERE id=?""",
            (message, now, now, task["id"]),
        )
        connection.execute(
            """UPDATE agents SET current_task_id=NULL,
            status=CASE WHEN is_paused=1 THEN 'paused' ELSE 'idle' END, updated_at=?
            WHERE id=? AND current_task_id=?""",
            (now, task["agent_id"], task["id"]),
        )
        add_event(connection, task["agent_id"], task["id"], "mission_cancelled", message)
        connection.commit()


def _fail_task(task: dict[str, Any], error: str) -> None:
    now = utc_now()
    safe_error = error[:1200]
    with connect() as connection:
        connection.execute(
            "UPDATE tasks SET status='failed', error=?, updated_at=?, completed_at=? WHERE id=?",
            (safe_error, now, now, task["id"]),
        )
        connection.execute(
            """UPDATE agents SET current_task_id=NULL,
            status=CASE WHEN is_paused=1 THEN 'paused' ELSE 'failed' END, updated_at=?
            WHERE id=? AND current_task_id=?""",
            (now, task["agent_id"], task["id"]),
        )
        add_event(connection, task["agent_id"], task["id"], "mission_failed",
                  f'Mission failed: {safe_error[:220]}')
        connection.commit()


async def _run_ollama_task(client: httpx.AsyncClient, task: dict[str, Any], model: str) -> str:
    system = (
        f"{SYSTEM_POLICY}\\n\\nYour assigned identity: {task['agent_name']} — {task['agent_role']} "
        f"in {task['agent_department']}. Agent capability profile: {task['agent_model_profile']}."
    )
    user = (
        f"MISSION TITLE: {task['title']}\\n\\nFOUNDER INSTRUCTIONS:\\n{task['instructions']}\\n\\n"
        "Return a clear deliverable. Include a concise summary, detailed result, assumptions, and next actions."
    )
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": True,
        "keep_alive": "10m",
        "options": {"temperature": 0.35},
    }
    chunks: list[str] = []
    last_progress_event = 0
    generated_length = 0
    async with client.stream(
        "POST", f"{OLLAMA_BASE_URL}/api/chat", json=payload,
        timeout=httpx.Timeout(MODEL_TIMEOUT, connect=5.0),
    ) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if _cancel_requested(task["id"]):
                raise MissionCancelled("Founder requested cancellation.")
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            content = item.get("message", {}).get("content", "")
            if content:
                chunks.append(content)
                generated_length += len(content)
            if item.get("done"):
                break
            progress = min(90, 12 + generated_length // 45)
            if progress >= last_progress_event + 12:
                _record_progress(task, progress, f"Local model response is being generated ({generated_length} characters received).")
                last_progress_event = progress
    if _cancel_requested(task["id"]):
        raise MissionCancelled("Founder requested cancellation.")
    result = "".join(chunks).strip()
    if not result:
        raise RuntimeError("Ollama returned an empty response.")
    return result


def _recover_interrupted_missions() -> None:
    now = utc_now()
    with connect() as connection:
        rows = connection.execute(
            "SELECT id, agent_id, title FROM tasks WHERE status='running'"
        ).fetchall()
        for row in rows:
            connection.execute(
                """UPDATE tasks SET status='queued', progress=0, cancel_requested=0,
                started_at=NULL, updated_at=?, error=NULL WHERE id=?""",
                (now, row["id"]),
            )
            connection.execute(
                """UPDATE agents SET status=CASE WHEN is_paused=1 THEN 'paused' ELSE 'queued' END,
                current_task_id=NULL, updated_at=? WHERE id=? AND current_task_id=?""",
                (now, row["agent_id"], row["id"]),
            )
            add_event(
                connection,
                row["agent_id"],
                row["id"],
                "worker_recovered",
                "Worker restarted; the unfinished mission was safely returned to the queue.",
            )
        connection.commit()


async def run_worker() -> None:
    _recover_interrupted_missions()
    poll = max(0.5, POLL_SECONDS)
    _heartbeat("running")
    print("AgentSINC local worker is running. Waiting for Ollama and queued missions.", flush=True)
    async with httpx.AsyncClient(timeout=httpx.Timeout(3.0, connect=1.5)) as client:
        models: list[str] = []
        last_model_check = 0.0
        while True:
            _heartbeat("running")
            now = asyncio.get_running_loop().time()
            if now - last_model_check >= 10 or not models:
                last_model_check = now
                try:
                    models = await _get_models(client)
                    set_runtime_value("ollama_state", "online")
                    set_runtime_value("ollama_models", json.dumps(models))
                except (httpx.HTTPError, ValueError):
                    models = []
                    set_runtime_value("ollama_state", "offline")
                    set_runtime_value("ollama_models", "[]")
            model = _choose_model(models)
            if not model:
                await asyncio.sleep(5)
                continue
            task = _claim_next_task()
            if not task:
                await asyncio.sleep(poll)
                continue
            try:
                print(f'Running mission {task["id"]} with {model}', flush=True)
                result = await _run_ollama_task(client, task, model)
                if _cancel_requested(task["id"]):
                    _cancel_task(task, "Mission cancelled by the founder.")
                else:
                    _finish_task(task, result)
                    print(f'Mission completed: {task["id"]}', flush=True)
            except MissionCancelled:
                _cancel_task(task, "Mission cancelled by the founder.")
            except (httpx.HTTPError, RuntimeError, ValueError) as exc:
                _fail_task(task, f"Local model error: {exc}")
                print(f'Mission failed: {task["id"]}: {exc}', flush=True)
            except Exception as exc:
                _fail_task(task, f"Unexpected worker error: {type(exc).__name__}: {exc}")
                print(f'Unexpected mission error: {exc}', flush=True)


def main() -> None:
    import signal

    async def serve() -> None:
        task = asyncio.create_task(run_worker(), name="agentsinc-worker")
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for signal_name in ("SIGINT", "SIGTERM"):
            sig = getattr(signal, signal_name, None)
            if sig is not None:
                try:
                    loop.add_signal_handler(sig, stop.set)
                except (NotImplementedError, RuntimeError):
                    pass
        try:
            await stop.wait()
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            set_runtime_value("worker_state", "stopped")
            set_runtime_value("worker_heartbeat", utc_now())
            print("AgentSINC local worker stopped.", flush=True)

    asyncio.run(serve())


if __name__ == "__main__":
    main()
