from __future__ import annotations

import pytest

from app.agent_write import write_agent_file
from app.workspace import WorkspaceError


def make_workspace(root):
    (root / "backend" / "app").mkdir(parents=True)
    (root / "backend" / "tests").mkdir(parents=True)
    (root / "frontend" / "src").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)


def test_agent_write_is_atomic_and_restricted_to_source_roots(tmp_path, monkeypatch) -> None:
    root = tmp_path / "workspace"
    make_workspace(root)
    monkeypatch.setenv("AGENTSINC_WORKSPACE_ROOT", str(root))

    result = write_agent_file("backend/app/example.py", "VALUE = 42\n")

    assert result["status"] == "written"
    assert (root / "backend" / "app" / "example.py").read_text() == "VALUE = 42\n"
    assert len(result["sha256"]) == 64


@pytest.mark.parametrize(
    "path",
    [
        "../outside.py",
        "/tmp/outside.py",
        "backend/.env",
        "backend/app/.env.local",
        "backend/requirements.txt",
        "frontend/package.json",
        "frontend/package-lock.json",
        "README.md",
    ],
)
def test_agent_write_refuses_unsafe_or_unapproved_paths(tmp_path, monkeypatch, path) -> None:
    root = tmp_path / "workspace"
    make_workspace(root)
    monkeypatch.setenv("AGENTSINC_WORKSPACE_ROOT", str(root))

    with pytest.raises(WorkspaceError):
        write_agent_file(path, "SAFE = True\n")


def test_agent_write_rejects_secret_like_content(tmp_path, monkeypatch) -> None:
    root = tmp_path / "workspace"
    make_workspace(root)
    monkeypatch.setenv("AGENTSINC_WORKSPACE_ROOT", str(root))

    with pytest.raises(WorkspaceError, match="credential-like"):
        write_agent_file("backend/app/settings.py", 'API_KEY = "private-key-value-123456"\n')


def test_agent_write_refuses_symlink_destinations(tmp_path, monkeypatch) -> None:
    root = tmp_path / "workspace"
    make_workspace(root)
    outside = tmp_path / "outside.py"
    outside.write_text("ORIGINAL = True\n")
    try:
        (root / "backend" / "app" / "link.py").symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("This platform does not permit creating a symlink in the test environment")
    monkeypatch.setenv("AGENTSINC_WORKSPACE_ROOT", str(root))

    with pytest.raises(WorkspaceError):
        write_agent_file("backend/app/link.py", "MODIFIED = True\n")
    assert outside.read_text() == "ORIGINAL = True\n"
