from __future__ import annotations

from app.db import (
    connect,
    create_task,
    init_db,
    recall_agent_memories,
    remember_completed_task,
)


def test_existing_database_is_additively_seeded_with_team_lead(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTSINC_DB_PATH", str(tmp_path / "migration.sqlite3"))
    init_db()

    with connect() as connection:
        connection.execute("DELETE FROM agents WHERE id='team_lead'")
        connection.commit()

    # Re-initialization simulates upgrading a database created before Team Lead existed.
    init_db()
    with connect() as connection:
        team_lead = connection.execute(
            "SELECT id, role FROM agents WHERE id='team_lead'"
        ).fetchone()

    assert team_lead is not None
    assert team_lead["role"] == "Execution Coordinator"


def test_completed_missions_become_bounded_local_memory_and_redact_secrets(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTSINC_DB_PATH", str(tmp_path / "learning-memory.sqlite3"))
    init_db()
    task = create_task(
        "developer",
        "Review SQLite mission persistence",
        "Inspect how queued missions and task lifecycle updates are persisted.",
    )

    with connect() as connection:
        remember_completed_task(
            connection,
            task,
            "Verified SQLite persistence and worker lifecycle. API_KEY=local-secret-token "
            "Authorization=Bearer very-long-private-token-value "
            "Authorization: Basic another-private-token-value",
        )
        connection.commit()

    memories = recall_agent_memories(
        "designer",
        "SQLite task lifecycle persistence",
        limit=3,
    )

    assert len(memories) == 1
    assert memories[0]["task_id"] == task["id"]
    assert "SQLite" in memories[0]["title"]
    assert "persistence" in memories[0]["title"].lower()
    assert "[REDACTED]" in memories[0]["content"]
    assert "local-secret-token" not in memories[0]["content"]
    assert "very-long-private-token-value" not in memories[0]["content"]

    # The records are stored in SQLite and survive database initialization.
    init_db()
    assert recall_agent_memories("developer", "SQLite persistence", limit=3)
