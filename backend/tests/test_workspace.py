from __future__ import annotations

from pathlib import Path

import pytest

from app.workspace import (
    WorkspaceError,
    build_workspace_context,
    list_workspace_files,
    read_workspace_file,
    safe_file_path,
    search_workspace,
    workspace_summary,
    redact_sensitive_text,
)


def _make_workspace(root: Path) -> Path:
    (root / "docs").mkdir(parents=True)
    (root / "backend" / "app").mkdir(parents=True)
    (root / "node_modules" / "example").mkdir(parents=True)
    (root / ".venv" / "Lib").mkdir(parents=True)
    (root / "secrets").mkdir(parents=True)
    (root / "README.md").write_text("# Example project\n", encoding="utf-8")
    (root / "docs" / "ARCHITECTURE.md").write_text(
        "FastAPI API, SQLite persistence and Ollama worker architecture.", encoding="utf-8"
    )
    (root / "backend" / "app" / "worker.py").write_text(
        "def process_mission():\n    return 'local ollama worker'\n", encoding="utf-8"
    )
    (root / ".env").write_text("API_KEY=should-not-be-readable", encoding="utf-8")
    (root / "secrets" / "token.txt").write_text("should-not-be-readable", encoding="utf-8")
    (root / "node_modules" / "example" / "index.js").write_text("dependency", encoding="utf-8")
    (root / ".venv" / "Lib" / "python.py").write_text("environment", encoding="utf-8")
    return root


def test_workspace_inventory_excludes_secrets_and_dependencies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _make_workspace(tmp_path / "AgentSINC")
    monkeypatch.setenv("AGENTSINC_WORKSPACE_ROOT", str(root))

    files = list_workspace_files()

    assert "README.md" in files
    assert "docs/ARCHITECTURE.md" in files
    assert "backend/app/worker.py" in files
    assert ".env" not in files
    assert "secrets/token.txt" not in files
    assert not any(path.startswith("node_modules/") for path in files)
    assert not any(path.startswith(".venv/") for path in files)


def test_safe_file_reader_blocks_traversal_and_absolute_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _make_workspace(tmp_path / "AgentSINC")
    outside = tmp_path / "outside.txt"
    outside.write_text("private", encoding="utf-8")
    monkeypatch.setenv("AGENTSINC_WORKSPACE_ROOT", str(root))

    with pytest.raises(WorkspaceError):
        safe_file_path("../outside.txt")
    with pytest.raises(WorkspaceError):
        safe_file_path(str(outside))
    with pytest.raises(WorkspaceError):
        safe_file_path(r"C:\Users\someone\.ssh\id_rsa")
    with pytest.raises(WorkspaceError):
        read_workspace_file(".env")


def test_search_and_context_return_actual_project_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _make_workspace(tmp_path / "AgentSINC")
    monkeypatch.setenv("AGENTSINC_WORKSPACE_ROOT", str(root))

    results = search_workspace("FastAPI SQLite Ollama worker", max_results=5)
    context = build_workspace_context("analyse backend architecture and Ollama worker")

    assert any(item["path"] == "docs/ARCHITECTURE.md" for item in results)
    assert "docs/ARCHITECTURE.md" in context.files
    assert "backend/app/worker.py" in context.files
    assert "local ollama worker" in context.text
    assert "should-not-be-readable" not in context.text


def test_workspace_summary_is_explicitly_read_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _make_workspace(tmp_path / "AgentSINC")
    monkeypatch.setenv("AGENTSINC_WORKSPACE_ROOT", str(root))

    summary = workspace_summary()

    assert summary["available"] is True
    assert summary["root_name"] == "AgentSINC"
    assert summary["read_only"] is True
    assert summary["sensitive_files_excluded"] is True


def test_redaction_removes_common_secret_values() -> None:
    source = (
        'API_KEY="test-secret-value-123"\\n'
        '{"access_token": "json-secret-token-123"}\\n'
        'Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456\\n'
        'github_pat_abcdefghijklmnopqrstuvwxyz123456\\n'
    )
    redacted = redact_sensitive_text(source)
    assert "test-secret-value-123" not in redacted
    assert "json-secret-token-123" not in redacted
    assert "abcdefghijklmnopqrstuvwxyz123456" not in redacted
    assert "REDACTED" in redacted
