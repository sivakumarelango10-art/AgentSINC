from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .db import (
    add_event, agent_to_dict, connect, create_task, create_orchestration,
    event_to_dict, get_orchestration_detail, init_db, orchestration_to_dict,
    set_runtime_value, task_to_dict, utc_now,
    claim_tool_approval, get_tool_approval, list_tool_approvals, resolve_tool_approval,
)
from .agent_write import write_agent_file
from .mcp_registry import MCPRegistry, MCPRegistryError, configured_mcp_server_count
from .research import google_search_is_enabled
from .sandbox import get_sandbox_status
from .workspace import WorkspaceError, list_workspace_files, read_workspace_file, search_workspace, workspace_summary


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_TIMEOUT = httpx.Timeout(2.0, connect=1.0)


class CreateTaskRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=3, max_length=120)
    instructions: str = Field(min_length=10, max_length=12000)


class CreateOrchestrationRequest(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    instructions: str = Field(min_length=20, max_length=12000)


class AgentControlRequest(BaseModel):
    action: Literal["pause", "resume"]


class SelectModelRequest(BaseModel):
    model: str = Field(min_length=1, max_length=160)


class SetAgentLocationRequest(BaseModel):
    location: Literal["desk", "command", "discussion", "meeting"]


class ResolveApprovalRequest(BaseModel):
    action: Literal["approve", "reject"]


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

    @app.get("/api/v1/integrations/mcp")
    async def mcp_integration_status() -> dict:
        try:
            registry = MCPRegistry()
        except MCPRegistryError as exc:
            return {"configured_count": 0, "servers": [], "error": str(exc)}

        role_results: dict[str, list[dict]] = {}
        for role in ("developer", "tester"):
            try:
                role_results[role] = await registry.discover(role)
            except MCPRegistryError as exc:
                role_results[role] = [{"name": "", "description": f"Discovery failed ({type(exc).__name__}).", "unavailable": True}]

        servers = []
        for config in registry.servers:
            agents = {}
            for role in ("developer", "tester"):
                if role not in config["roles"]:
                    continue
                matching = [item for item in role_results.get(role, []) if item.get("name", "").startswith(f'mcp.{config["name"]}.')]
                error = next((item["description"] for item in matching if item.get("unavailable")), None)
                tools = sorted(item["tool_name"] for item in matching if not item.get("unavailable") and item.get("tool_name"))
                agents[role] = {"connected": bool(tools) and error is None, "tools": tools, "error": error}
            servers.append({"name": config["name"], "transport": config["transport"], "roles": config["roles"], "agents": agents})
        return {"configured_count": len(servers), "servers": servers, "error": None}

    @app.get("/api/v1/overview")
    async def overview() -> dict:
        with connect() as connection:
            agent_rows = connection.execute(
                "SELECT * FROM agents ORDER BY CASE id WHEN 'ceo' THEN 0 WHEN 'team_lead' THEN 1 ELSE 2 END, name"
            ).fetchall()
            task_rows = connection.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 100").fetchall()
            event_rows = connection.execute("SELECT * FROM events ORDER BY id DESC LIMIT 80").fetchall()
            memory_records = connection.execute("SELECT COUNT(*) FROM agent_memory").fetchone()[0]
            runtime_rows = connection.execute("SELECT key, value, updated_at FROM runtime_state").fetchall()
            orchestration_rows = connection.execute(
                "SELECT * FROM orchestrations ORDER BY created_at DESC LIMIT 30"
            ).fetchall()
            active_orchestration = connection.execute(
                "SELECT * FROM orchestrations WHERE status='running' ORDER BY created_at ASC LIMIT 1"
            ).fetchone()
            active_orchestration_progress = connection.execute(
                """SELECT AVG(progress) AS progress FROM tasks
                WHERE orchestration_id=?""",
                (active_orchestration["id"],),
            ).fetchone()["progress"] if active_orchestration else 0
            current_tasks = connection.execute(
                """SELECT t.* FROM tasks t
                WHERE t.status IN ('queued', 'running')
                ORDER BY CASE t.status WHEN 'running' THEN 0 ELSE 1 END, t.created_at"""
            ).fetchall()
            orchestration_agent_ids = set()
            if active_orchestration:
                orchestration_agent_ids = {
                    row["agent_id"] for row in connection.execute(
                        "SELECT DISTINCT agent_id FROM tasks WHERE orchestration_id=?",
                        (active_orchestration["id"],),
                    ).fetchall()
                }

        task_map = {row["id"]: task_to_dict(row) for row in current_tasks}
        latest_activity_by_agent: dict[str, str] = {}
        recent_tool_events_by_agent: dict[str, list[dict[str, Any]]] = {}
        # event_rows are newest-first. Keep a small, real execution trace per agent.
        for event in event_rows:
            latest_activity_by_agent.setdefault(event["agent_id"], event["message"])
            if str(event["event_type"]).startswith("tool_"):
                bucket = recent_tool_events_by_agent.setdefault(event["agent_id"], [])
                if len(bucket) < 5:
                    bucket.append(event_to_dict(event))

        agents = []
        for row in agent_rows:
            item = agent_to_dict(row)
            item["recentToolEvents"] = recent_tool_events_by_agent.get(row["id"], [])
            if row["id"] == "team_lead" and active_orchestration:
                item["currentTask"] = active_orchestration["title"]
                item["taskStatus"] = "running"
                item["latestResult"] = active_orchestration["result"]
                item["latestTaskUpdatedAt"] = active_orchestration["updated_at"]
                item["progress"] = round(active_orchestration_progress or 0)
                item["status"] = "paused" if item["paused"] else (
                    "thinking" if active_orchestration["stage"] in ("planning", "synthesizing")
                    else "collaborating"
                )
                # The Team Lead's 3D destination is derived from the persisted
                # orchestration lifecycle, never from an animation-only timer.
                stage = active_orchestration["stage"]
                item["location"] = (
                    "discussion" if stage == "executing"
                    else "meeting" if stage == "synthesizing"
                    else "command"
                )
                item["latestActivity"] = latest_activity_by_agent.get(
                    row["id"], "Team Lead is coordinating the current request."
                )
                agents.append(item)
                continue
            current = task_map.get(row["current_task_id"])
            latest_task_row = next(
                (task for task in task_rows if task["agent_id"] == row["id"]),
                None,
            )
            latest_task = task_to_dict(latest_task_row) if latest_task_row else None
            displayed_task = current or latest_task
            if displayed_task:
                item["currentTask"] = displayed_task["title"]
                item["taskStatus"] = displayed_task["status"]
                item["latestResult"] = displayed_task.get("result") or displayed_task.get("error")
                item["latestTaskUpdatedAt"] = displayed_task["updated_at"]
                item["progress"] = displayed_task["progress"]
            if current:
                item["status"] = (
                    "waiting" if row["status"] == "waiting"
                    else "working" if current["status"] == "running"
                    else ("paused" if item["paused"] else "queued")
                )
            elif item["paused"]:
                item["status"] = "paused"
            else:
                queued = next((t for t in task_map.values() if t["agent_id"] == item["id"]), None)
                item["status"] = "paused" if item["paused"] else (
                    "queued" if queued else ("failed" if row["status"] == "failed" else "idle")
                )
            # Specialists assigned under one active Team Lead orchestration physically
            # gather in the discussion room while child missions run, then in the
            # conference room while the Team Lead synthesizes their real outputs.
            # Once synthesis ends, the persisted home destination is restored.
            if active_orchestration and row["id"] in orchestration_agent_ids:
                if active_orchestration["stage"] == "executing":
                    item["location"] = "discussion"
                elif active_orchestration["stage"] == "synthesizing":
                    item["location"] = "meeting"
                else:
                    item["location"] = row["location"]
            else:
                item["location"] = row["location"]
            item["latestActivity"] = latest_activity_by_agent.get(
                row["id"], "Waiting for a mission assignment."
            )
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

        last_generation_metrics: dict[str, Any] = {}
        try:
            parsed_metrics = json.loads(state.get("last_generation_metrics", {}).get("value") or "{}")
            if isinstance(parsed_metrics, dict):
                last_generation_metrics = parsed_metrics
        except (TypeError, ValueError):
            last_generation_metrics = {}

        sandbox_status = get_sandbox_status()
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
            "orchestrations": [get_orchestration_detail(row["id"]) for row in orchestration_rows],
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
                "last_generation_metrics": last_generation_metrics,
                "memory_records": memory_records,
                "google_search_enabled": google_search_is_enabled(),
                "agent_harness_enabled": os.getenv("AGENTSINC_AGENT_HARNESS_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"},
                "sandbox_available": sandbox_status["available"],
                "sandbox_status": sandbox_status,
                "mcp_configured_servers": configured_mcp_server_count(),
                "pending_approvals": len(list_tool_approvals("pending", 200)),
            },
        }

    @app.get("/api/v1/approvals")
    def read_tool_approvals(
        status: Literal["pending", "approved", "rejected", "failed", "all"] = Query(default="pending"),
        limit: int = Query(default=100, ge=1, le=200),
    ) -> dict:
        return {"approvals": list_tool_approvals(status, limit)}

    @app.post("/api/v1/approvals/{approval_id}/resolve")
    async def decide_tool_approval(approval_id: str, payload: ResolveApprovalRequest) -> dict:
        approval = get_tool_approval(approval_id)
        if not approval:
            raise HTTPException(status_code=404, detail="Tool approval request not found.")
        if approval["status"] != "pending":
            raise HTTPException(status_code=409, detail="This tool approval was already resolved.")

        if payload.action == "reject":
            try:
                resolved = resolve_tool_approval(
                    approval_id, "rejected", "Founder rejected this action. No change was made."
                )
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            return {"approval": resolved}

        # Claim the approval atomically before the first side effect.
        # This also verifies the task is still running and wasn't cancelled.
        claimed = claim_tool_approval(approval_id)
        if not claimed:
            latest = get_tool_approval(approval_id)
            raise HTTPException(
                status_code=409,
                detail=(
                    latest.get("result") if latest and latest.get("result")
                    else "This approval is no longer pending or its mission has stopped."
                ),
            )

        tool_name = claimed["tool_name"]
        arguments = claimed["payload"] or {}
        try:
            if tool_name == "workspace.write_file":
                result = write_agent_file(
                    str(arguments.get("path") or ""),
                    str(arguments.get("content") or ""),
                )
                result_text = json.dumps({
                    "status": result["status"],
                    "path": result["path"],
                    "bytes_written": result["bytes_written"],
                    "sha256": result["sha256"],
                    "summary": str(arguments.get("summary") or "")[:500],
                })
            elif tool_name.startswith("mcp."):
                parts = tool_name.split(".", 2)
                if len(parts) != 3:
                    raise MCPRegistryError("Invalid MCP tool identifier.")
                registry = MCPRegistry()
                result = await registry.call_tool(
                    approval["agent_id"],
                    str(arguments.get("server_name") or parts[1]),
                    str(arguments.get("tool_name") or parts[2]),
                    arguments.get("arguments") if isinstance(arguments.get("arguments"), dict) else {},
                )
                result_text = json.dumps(result, ensure_ascii=False)[:12000]
            else:
                raise HTTPException(status_code=422, detail="This tool type cannot be approved by this endpoint.")
        except HTTPException:
            raise
        except (WorkspaceError, MCPRegistryError, ValueError, OSError) as exc:
            try:
                failed = resolve_tool_approval(approval_id, "failed", f"Approved action failed: {exc}")
            except ValueError:
                failed = get_tool_approval(approval_id)
            return {"approval": failed, "error": str(exc)}
        except Exception as exc:
            try:
                failed = resolve_tool_approval(
                    approval_id, "failed", f"Approved action failed ({type(exc).__name__})."
                )
            except ValueError:
                failed = get_tool_approval(approval_id)
            return {"approval": failed, "error": f"Approved action failed ({type(exc).__name__})."}

        try:
            resolved = resolve_tool_approval(approval_id, "approved", result_text)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"approval": resolved}

    @app.post("/api/v1/orchestrations", status_code=201)
    def submit_orchestration(payload: CreateOrchestrationRequest) -> dict:
        orchestration = create_orchestration(payload.title, payload.instructions)
        return {"orchestration": orchestration}

    @app.get("/api/v1/orchestrations/{orchestration_id}")
    def read_orchestration(orchestration_id: str) -> dict:
        orchestration = get_orchestration_detail(orchestration_id)
        if not orchestration:
            raise HTTPException(status_code=404, detail="CEO orchestration not found.")
        return {"orchestration": orchestration}

    @app.post("/api/v1/orchestrations/{orchestration_id}/cancel")
    def cancel_orchestration(orchestration_id: str) -> dict:
        with connect() as connection:
            orchestration = connection.execute(
                "SELECT * FROM orchestrations WHERE id=?", (orchestration_id,)
            ).fetchone()
            if not orchestration:
                raise HTTPException(status_code=404, detail="CEO orchestration not found.")
            if orchestration["status"] in ("completed", "failed", "cancelled"):
                raise HTTPException(status_code=409, detail="This orchestration is already finished.")
            now = utc_now()
            connection.execute(
                "UPDATE orchestrations SET cancel_requested=1, updated_at=? WHERE id=?",
                (now, orchestration_id),
            )
            connection.execute(
                """UPDATE tasks SET status='cancelled', updated_at=?, completed_at=?, error='Cancelled with parent CEO request'
                WHERE orchestration_id=? AND status='queued'""",
                (now, now, orchestration_id),
            )
            connection.execute(
                """UPDATE agents SET status=CASE WHEN is_paused=1 THEN 'paused' ELSE 'idle' END,
                updated_at=? WHERE current_task_id IS NULL
                AND id IN (SELECT agent_id FROM tasks WHERE orchestration_id=? AND status='cancelled')""",
                (now, orchestration_id),
            )
            connection.execute(
                """UPDATE tasks SET cancel_requested=1, updated_at=?
                WHERE orchestration_id=? AND status='running'""",
                (now, orchestration_id),
            )
            remaining = connection.execute(
                "SELECT COUNT(*) FROM tasks WHERE orchestration_id=? AND status='running'",
                (orchestration_id,),
            ).fetchone()[0]
            if orchestration["status"] == "queued" or (
                orchestration["stage"] == "executing" and remaining == 0
            ):
                connection.execute(
                    "UPDATE orchestrations SET status='cancelled', stage='cancelled', completed_at=?, updated_at=? WHERE id=?",
                    (now, now, orchestration_id),
                )
                connection.execute(
                    "UPDATE agents SET status=CASE WHEN is_paused=1 THEN 'paused' ELSE 'idle' END, updated_at=? WHERE id='ceo'",
                    (now,),
                )
            add_event(
                connection, "ceo", None, "orchestration_cancel_requested",
                "Founder requested cancellation of the CEO orchestration.",
                orchestration_id=orchestration_id,
            )
            connection.commit()
        return {"ok": True, "orchestration_id": orchestration_id}

    @app.get("/api/v1/workspace/summary")
    def get_workspace_summary() -> dict:
        try:
            return workspace_summary()
        except WorkspaceError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/v1/workspace/files")
    def get_workspace_files(limit: int = Query(default=200, ge=1, le=500)) -> dict:
        try:
            return {"files": list_workspace_files(limit=limit)}
        except WorkspaceError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/v1/workspace/read")
    def get_workspace_file(
        path: str = Query(min_length=1, max_length=300),
        max_chars: int = Query(default=12000, ge=500, le=24000),
    ) -> dict:
        try:
            return {"path": path, "content": read_workspace_file(path, max_chars=max_chars)}
        except WorkspaceError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/v1/workspace/search")
    def search_workspace_files(
        q: str = Query(min_length=2, max_length=300),
        limit: int = Query(default=12, ge=1, le=30),
    ) -> dict:
        try:
            return {"results": search_workspace(q, max_results=limit)}
        except WorkspaceError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

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

    @app.post("/api/v1/agents/{agent_id}/location")
    def move_agent(agent_id: str, payload: SetAgentLocationRequest) -> dict:
        with connect() as connection:
            agent = connection.execute("SELECT * FROM agents WHERE id=?", (agent_id,)).fetchone()
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found.")
            if agent_id == "team_lead":
                active = connection.execute(
                    "SELECT 1 FROM orchestrations WHERE status='running' LIMIT 1"
                ).fetchone()
                if active:
                    raise HTTPException(
                        status_code=409,
                        detail="The Team Lead is following an active orchestration route. Move them after it finishes.",
                    )
            now = utc_now()
            connection.execute(
                "UPDATE agents SET location=?, updated_at=? WHERE id=?",
                (payload.location, now, agent_id),
            )
            add_event(
                connection,
                agent_id,
                agent["current_task_id"],
                "agent_location_changed",
                f'{agent["name"]} was sent to the {payload.location.replace("_", " ")}.',
            )
            connection.commit()
        return {"ok": True, "agent_id": agent_id, "location": payload.location}

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
