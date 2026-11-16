from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


AGENTS: list[dict[str, Any]] = [
    {"id": "ceo", "name": "SINC CEO", "role": "Chief Orchestrator", "department": "Command Hub", "color": "#7C3AED", "model_profile": "Orchestrator", "position": [0, 0, -4.5]},
    {"id": "developer", "name": "Dev Agent", "role": "Developer", "department": "Development Studio", "color": "#0EA5E9", "model_profile": "Code Specialist", "position": [-6.3, 0, -0.9]},
    {"id": "designer", "name": "Design Agent", "role": "Designer", "department": "Design Studio", "color": "#EC4899", "model_profile": "Visual Specialist", "position": [6.3, 0, -0.9]},
    {"id": "researcher", "name": "Research Agent", "role": "Researcher", "department": "Research Library", "color": "#D97706", "model_profile": "Research Specialist", "position": [-6.3, 0, 4.25]},
    {"id": "tester", "name": "QA Agent", "role": "Tester", "department": "Quality Lab", "color": "#16A34A", "model_profile": "Quality Specialist", "position": [6.3, 0, 4.25]},
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def database_path() -> Path:
    configured = os.getenv("AGENTSINC_DB_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[1] / "data" / "agentsinc.sqlite3"


def connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def init_db() -> None:
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                department TEXT NOT NULL,
                color TEXT NOT NULL,
                model_profile TEXT NOT NULL,
                position_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'idle',
                is_paused INTEGER NOT NULL DEFAULT 0,
                current_task_id TEXT,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL REFERENCES agents(id),
                title TEXT NOT NULL,
                instructions TEXT NOT NULL,
                status TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0,
                result TEXT,
                error TEXT,
                cancel_requested INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL REFERENCES agents(id),
                task_id TEXT REFERENCES tasks(id),
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS runtime_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_status_created ON tasks(status, created_at);
            CREATE INDEX IF NOT EXISTS idx_tasks_agent_created ON tasks(agent_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_events_agent_created ON events(agent_id, created_at DESC);
            """
        )
        existing = connection.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        if existing == 0:
            now = utc_now()
            for agent in AGENTS:
                connection.execute(
                    """INSERT INTO agents
                    (id, name, role, department, color, model_profile, position_json, status, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'idle', ?)""",
                    (agent["id"], agent["name"], agent["role"], agent["department"], agent["color"],
                     agent["model_profile"], json.dumps(agent["position"]), now),
                )
        connection.commit()


def add_event(connection: sqlite3.Connection, agent_id: str, task_id: str | None, event_type: str, message: str) -> None:
    connection.execute(
        "INSERT INTO events (agent_id, task_id, event_type, message, created_at) VALUES (?, ?, ?, ?, ?)",
        (agent_id, task_id, event_type, message, utc_now()),
    )


def set_runtime_value(key: str, value: str) -> None:
    now = utc_now()
    with connect() as connection:
        connection.execute(
            """INSERT INTO runtime_state (key, value, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
            (key, value, now),
        )
        connection.commit()


def get_runtime_value(key: str, default: str | None = None) -> str | None:
    with connect() as connection:
        row = connection.execute("SELECT value FROM runtime_state WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def agent_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"], "name": row["name"], "role": row["role"], "department": row["department"],
        "color": row["color"], "model": row["model_profile"], "position": json.loads(row["position_json"]),
        "status": row["status"], "paused": bool(row["is_paused"]), "current_task_id": row["current_task_id"],
        "currentTask": "No active mission assigned", "progress": 0, "updated_at": row["updated_at"],
    }


def task_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"], "agent_id": row["agent_id"], "title": row["title"],
        "instructions": row["instructions"], "status": row["status"], "progress": row["progress"],
        "result": row["result"], "error": row["error"], "cancel_requested": bool(row["cancel_requested"]),
        "created_at": row["created_at"], "updated_at": row["updated_at"],
        "started_at": row["started_at"], "completed_at": row["completed_at"],
    }


def event_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"], "agent_id": row["agent_id"], "task_id": row["task_id"],
        "event_type": row["event_type"], "message": row["message"], "created_at": row["created_at"],
    }


def create_task(agent_id: str, title: str, instructions: str) -> dict[str, Any]:
    task_id = str(uuid4())
    now = utc_now()
    with connect() as connection:
        agent = connection.execute("SELECT id, is_paused FROM agents WHERE id = ?", (agent_id,)).fetchone()
        if not agent:
            raise ValueError("Unknown agent.")
        if agent["is_paused"]:
            raise PermissionError("This agent is paused. Resume it before assigning a mission.")
        connection.execute(
            """INSERT INTO tasks
            (id, agent_id, title, instructions, status, progress, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'queued', 0, ?, ?)""",
            (task_id, agent_id, title.strip(), instructions.strip(), now, now),
        )
        connection.execute(
            "UPDATE agents SET status='queued', updated_at=? WHERE id=? AND current_task_id IS NULL",
            (now, agent_id),
        )
        add_event(connection, agent_id, task_id, "mission_queued", f'Mission queued: "{title.strip()}"')
        row = connection.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        connection.commit()
        return task_to_dict(row)
