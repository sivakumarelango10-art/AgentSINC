from __future__ import annotations

from fastapi.testclient import TestClient

from app.db import connect, create_task, create_tool_approval, init_db
from app.main import app


client = TestClient(app)


def _running_developer_task() -> str:
    task = create_task(
        "developer",
        "Implement an approved source change",
        "Update the sample documentation using the founder approval workflow.",
    )
    with connect() as connection:
        connection.execute(
            "UPDATE tasks SET status='running', progress=20 WHERE id=?",
            (task["id"],),
        )
        connection.execute(
            "UPDATE agents SET status='working', current_task_id=? WHERE id='developer'",
            (task["id"],),
        )
        connection.commit()
    return task["id"]


def _workspace(root):
    (root / "docs").mkdir(parents=True)
    (root / "backend" / "app").mkdir(parents=True)
    (root / "backend" / "tests").mkdir(parents=True)
    (root / "frontend" / "src").mkdir(parents=True)


def test_approval_can_be_rejected_without_executing_a_write(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTSINC_DB_PATH", str(tmp_path / "approvals.sqlite3"))
    init_db()
    task_id = _running_developer_task()
    approval = create_tool_approval(
        task_id,
        "developer",
        "workspace.write_file",
        {"path": "docs/never-written.md", "content": "SHOULD_NOT_WRITE = True", "summary": "Proposed write"},
    )

    listed = client.get("/api/v1/approvals")
    assert listed.status_code == 200
    assert listed.json()["approvals"][0]["id"] == approval["id"]

    rejected = client.post(
        f"/api/v1/approvals/{approval['id']}/resolve",
        json={"action": "reject"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["approval"]["status"] == "rejected"


def test_approved_file_write_executes_only_the_stored_payload(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTSINC_DB_PATH", str(tmp_path / "approvals.sqlite3"))
    root = tmp_path / "workspace"
    _workspace(root)
    monkeypatch.setenv("AGENTSINC_WORKSPACE_ROOT", str(root))
    init_db()
    task_id = _running_developer_task()
    approval = create_tool_approval(
        task_id,
        "developer",
        "workspace.write_file",
        {"path": "docs/approved-change.md", "content": "# Approved\n", "summary": "Document the workflow"},
    )

    result = client.post(
        f"/api/v1/approvals/{approval['id']}/resolve",
        json={"action": "approve"},
    )
    assert result.status_code == 200
    assert result.json()["approval"]["status"] == "approved"
    assert (root / "docs" / "approved-change.md").read_text() == "# Approved\n"


def test_approval_cannot_be_resolved_twice(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTSINC_DB_PATH", str(tmp_path / "approvals.sqlite3"))
    init_db()
    task_id = _running_developer_task()
    approval = create_tool_approval(task_id, "developer", "workspace.write_file", {
        "path": "docs/example.md", "content": "Example", "summary": "A proposed example"
    })
    first = client.post(f"/api/v1/approvals/{approval['id']}/resolve", json={"action": "reject"})
    second = client.post(f"/api/v1/approvals/{approval['id']}/resolve", json={"action": "approve"})
    assert first.status_code == 200
    assert second.status_code == 409
