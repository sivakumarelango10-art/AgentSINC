from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .db import add_event, agent_to_dict, connect, create_task, event_to_dict, init_db, set_runtime_value, task_to_dict, utc_now


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_TIMEOUT = httpx.Timeout(2.0, connect=1.0)


class CreateTaskRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=3, max_length=120)
    instructions: str = Field(min_length=10, max_length=12000)


class AgentControlRequest(BaseModel):
    action: Literal["pause", "resume"]


class SelectModelRequest(BaseModel):
    model: str = Field(min_length=1, max_length=160)


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(
        title="AgentSINC Local Runtime",
        version="0.1.0",
        description="Local-first agent task runtime powered by Ollama and SQLite.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    @app.get("/healthz")
    def healthz() -> dict:
        with connect() as connection:
            connection.execute("SELECT 1").fetchone()
        return {"status": "ok", "service": "agentsinc-local-runtime"}

    @app.get("/api/v1/overview")
    async def overview() -> dict:
        with connect() as connection:
            agent_rows = connection.execute(
                "SELECT * FROM agents ORDER BY CASE id WHEN 'ceo' THEN 0 ELSE 1 END, name"
            ).fetchall()
            task_rows = connection.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 100").fetchall()
            event_rows = connection.execute("SELECT * FROM events ORDER BY id DESC LIMIT 80").fetchall()
            runtime_rows = connection.execute("SELECT key, value, updated_at FROM runtime_state").fetchall()
            current_tasks = connection.execute(
                """SELECT t.* FROM tasks t
                WHERE t.status IN ('queued', 'running')
                ORDER BY CASE t.status WHEN 'running' THEN 0 ELSE 1 END, t.created_at"""
            ).fetchall()

        task_map = {row["id"]: task_to_dict(row) for row in current_tasks}
        agents = []
        for row in agent_rows:
            item = agent_to_dict(row)
            current = task_map.get(row["current_task_id"])
            if current:
                item["currentTask"] = current["title"]
                item["progress"] = current["progress"]
                item["status"] = "paused" if item["paused"] else (
                    "working" if current["status"] == "running" else "queued"
                )
            elif item["paused"]:
                item["status"] = "paused"
            else:
                queued = next((t for t in task_map.values() if t["agent_id"] == item["id"]), None)
                item["status"] = "queued" if queued else "idle"
            agents.append(item)

        state = {row["key"]: {"value": row["value"], "updated_at": row["updated_at"]} for row in runtime_rows}
        heartbeat = state.get("worker_heartbeat", {}).get("value")
        worker_state = state.get("worker_state", {}).get("value", "stopped")
        worker_online = False
        if heartbeat:
            try:
                heartbeat_time = datetime.fromisoformat(heartbeat)
                if heartbeat_time.tzinfo is None:
                    heartbeat_time = heartbeat_time.replace(tzinfo=timezone.utc)
                worker_online = (
                    (datetime.now(timezone.utc) - heartbeat_time).total_seconds() < 12
                    and worker_state == "running"
                )
            except ValueError:
                worker_online = False

        ollama_online = False
        models: list[str] = []
        try:
            async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
                response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
                response.raise_for_status()
                payload = response.json()
                models = sorted(
                    [str(model.get("name", "")) for model in payload.get("models", []) if model.get("name")]
                )
                ollama_online = True
        except (httpx.HTTPError, ValueError):
            ollama_online = False

        selected_model = state.get("selected_model", {}).get("value") or os.getenv("AGENTSINC_OLLAMA_MODEL")
        if selected_model and selected_model not in models:
            selected_model = None
        if not selected_model and models:
            selected_model = next(
                (name for name in models if any(token in name.lower() for token in ("qwen", "llama", "mistral", "gemma"))),
                models[0],
            )

        return {
            "agents": agents,
            "tasks": [task_to_dict(row) for row in task_rows],
            "events": [event_to_dict(row) for row in event_rows],
            "runtime": {
                "api_connected": True,
                "worker_online": worker_online,
                "worker_state": worker_state,
                "worker_heartbeat": heartbeat,
                "ollama_online": ollama_online,
                "models": models,
                "selected_model": selected_model,
                "zero_cost_mode": True,
                "execution_mode": "local-ollama",
            },
        }

    @app.get("/api/v1/agents/{agent_id}/events")
    def agent_events(agent_id: str, limit: int = 50) -> dict:
        bounded_limit = max(1, min(limit, 200))
        with connect() as connection:
            exists = connection.execute("SELECT id FROM agents WHERE id=?", (agent_id,)).fetchone()
            if not exists:
                raise HTTPException(status_code=404, detail="Agent not found.")
            rows = connection.execute(
                "SELECT * FROM events WHERE agent_id=? ORDER BY id DESC LIMIT ?",
                (agent_id, bounded_limit),
            ).fetchall()
        return {"events": [event_to_dict(row) for row in rows]}

    @app.post("/api/v1/tasks", status_code=201)
    def assign_task(payload: CreateTaskRequest) -> dict:
        try:
            return {"task": create_task(payload.agent_id, payload.title, payload.instructions)}
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/v1/tasks/{task_id}/cancel")
    def cancel_task(task_id: str) -> dict:
        with connect() as connection:
            task = connection.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not task:
                raise HTTPException(status_code=404, detail="Mission not found.")
            if task["status"] in ("completed", "failed", "cancelled"):
                raise HTTPException(status_code=409, detail="This mission is already finished.")
            now = utc_now()
            if task["status"] == "queued":
                connection.execute(
                    "UPDATE tasks SET status='cancelled', updated_at=?, completed_at=? WHERE id=?",
                    (now, now, task_id),
                )
                connection.execute(
                    """UPDATE agents SET status=CASE WHEN is_paused=1 THEN 'paused' ELSE 'idle' END, updated_at=?
                    WHERE id=? AND current_task_id IS NULL""",
                    (now, task["agent_id"]),
                )
                add_event(connection, task["agent_id"], task_id, "mission_cancelled", "Queued mission cancelled by the founder.")
            else:
                connection.execute(
                    "UPDATE tasks SET cancel_requested=1, updated_at=? WHERE id=?",
                    (now, task_id),
                )
                add_event(connection, task["agent_id"], task_id, "cancel_requested", "Cancellation requested. The local worker will stop generation.")
            connection.commit()
        return {"ok": True, "task_id": task_id}

    @app.post("/api/v1/tasks/{task_id}/retry")
    def retry_task(task_id: str) -> dict:
        with connect() as connection:
            task = connection.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not task:
                raise HTTPException(status_code=404, detail="Mission not found.")
            if task["status"] not in ("failed", "cancelled"):
                raise HTTPException(status_code=409, detail="Only failed or cancelled missions can be retried.")
            agent = connection.execute("SELECT is_paused FROM agents WHERE id=?", (task["agent_id"],)).fetchone()
            if agent and agent["is_paused"]:
                raise HTTPException(status_code=409, detail="Resume this agent before retrying.")
            now = utc_now()
            connection.execute(
                """UPDATE tasks SET status='queued', progress=0, result=NULL, error=NULL,
                cancel_requested=0, updated_at=?, started_at=NULL, completed_at=NULL WHERE id=?""",
                (now, task_id),
            )
            connection.execute(
                "UPDATE agents SET status='queued', updated_at=? WHERE id=? AND current_task_id IS NULL",
                (now, task["agent_id"]),
            )
            add_event(connection, task["agent_id"], task_id, "mission_retried", "Mission added back to the local queue.")
            updated = connection.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            connection.commit()
        return {"task": task_to_dict(updated)}

    @app.post("/api/v1/agents/{agent_id}/control")
    def control_agent(agent_id: str, payload: AgentControlRequest) -> dict:
        with connect() as connection:
            agent = connection.execute("SELECT * FROM agents WHERE id=?", (agent_id,)).fetchone()
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found.")
            now = utc_now()
            paused = 1 if payload.action == "pause" else 0
            if payload.action == "pause":
                connection.execute(
                    """UPDATE agents SET is_paused=1,
                    status=CASE WHEN current_task_id IS NULL THEN 'paused' ELSE status END,
                    updated_at=? WHERE id=?""",
                    (now, agent_id),
                )
                message = "Agent paused. New missions will wait; any in-flight local model response is allowed to finish."
                event_type = "agent_paused"
            else:
                connection.execute(
                    """UPDATE agents SET is_paused=0,
                    status=CASE WHEN current_task_id IS NULL THEN
                        CASE WHEN EXISTS(SELECT 1 FROM tasks WHERE agent_id=? AND status='queued') THEN 'queued' ELSE 'idle' END
                        ELSE status END,
                    updated_at=? WHERE id=?""",
                    (agent_id, now, agent_id),
                )
                message = "Agent resumed and available for queued missions."
                event_type = "agent_resumed"
            add_event(connection, agent_id, agent["current_task_id"], event_type, message)
            connection.commit()
        return {"ok": True, "agent_id": agent_id, "paused": bool(paused), "message": message}

    @app.patch("/api/v1/runtime/model")
    async def select_model(payload: SelectModelRequest) -> dict:
        try:
            async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
                response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
                response.raise_for_status()
                available = {
                    str(model.get("name"))
                    for model in response.json().get("models", [])
                    if model.get("name")
                }
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(status_code=503, detail="Ollama is not reachable on this computer.") from exc
        if payload.model not in available:
            raise HTTPException(status_code=404, detail="That model is not installed in Ollama.")
        set_runtime_value("selected_model", payload.model)
        return {"ok": True, "selected_model": payload.model}

    return app


app = create_app()
