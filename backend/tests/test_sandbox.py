from __future__ import annotations

import pytest

from app.sandbox import run_test_suite


def test_sandbox_refuses_unknown_suites() -> None:
    with pytest.raises(ValueError, match="Unsupported test suite"):
        run_test_suite("arbitrary-shell-command")


def test_sandbox_does_not_fall_back_to_host_shell(monkeypatch) -> None:
    monkeypatch.setattr("app.sandbox.shutil.which", lambda _name: None)
    result = run_test_suite("python-tests")
    assert result["status"] == "not_run"
    assert "no host-shell fallback" in result["reason"]


def test_sandbox_requires_explicit_image(monkeypatch) -> None:
    monkeypatch.setattr("app.sandbox.shutil.which", lambda _name: "/usr/bin/docker")
    monkeypatch.delenv("AGENTSINC_SANDBOX_IMAGE", raising=False)
    result = run_test_suite("python-tests")
    assert result["status"] == "not_run"
    assert "not configured" in result["reason"]



def test_python_sandbox_suites_use_python3_available_in_image() -> None:
    from app.sandbox import TEST_SUITES

    assert "python3 -m pytest" in TEST_SUITES["python-tests"][1]
    assert "python3 -c" in TEST_SUITES["python-syntax"][1]
    assert "python -m pytest" not in TEST_SUITES["python-tests"][1]


def test_sandbox_status_reports_ready_only_when_daemon_and_image_exist(monkeypatch) -> None:
    import subprocess
    from app.sandbox import get_sandbox_status

    monkeypatch.setenv("AGENTSINC_SANDBOX_IMAGE", "agentsinc-sandbox:local")
    monkeypatch.setattr("app.sandbox.shutil.which", lambda _: "C:/Docker/docker.exe")
    monkeypatch.setattr(
        "app.sandbox.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, stdout="sha256:abc", stderr=""),
    )

    status = get_sandbox_status()
    assert status["available"] is True
    assert status["docker_cli_available"] is True
    assert status["docker_daemon_available"] is True
    assert status["image_available"] is True


def test_sandbox_status_explains_missing_image(monkeypatch) -> None:
    import subprocess
    from app.sandbox import get_sandbox_status

    monkeypatch.setenv("AGENTSINC_SANDBOX_IMAGE", "agentsinc-sandbox:local")
    monkeypatch.setattr("app.sandbox.shutil.which", lambda _: "C:/Docker/docker.exe")
    monkeypatch.setattr(
        "app.sandbox.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, stdout="", stderr="No such image: agentsinc-sandbox:local"),
    )

    status = get_sandbox_status()
    assert status["available"] is False
    assert status["docker_daemon_available"] is True
    assert status["image_available"] is False
    assert "Build it" in status["reason"]


def test_sandbox_status_explains_unreachable_docker_engine(monkeypatch) -> None:
    import subprocess
    from app.sandbox import get_sandbox_status

    monkeypatch.setenv("AGENTSINC_SANDBOX_IMAGE", "agentsinc-sandbox:local")
    monkeypatch.setattr("app.sandbox.shutil.which", lambda _: "C:/Docker/docker.exe")
    monkeypatch.setattr(
        "app.sandbox.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, stdout="", stderr="failed to connect to the Docker API"),
    )

    status = get_sandbox_status()
    assert status["available"] is False
    assert status["docker_daemon_available"] is False
    assert "engine is not reachable" in status["reason"]



def test_frontend_build_copies_dependencies_inside_turbopack_workspace() -> None:
    from app.sandbox import TEST_SUITES, _build_workspace_bootstrap

    working_directory, command = TEST_SUITES["frontend-build"]
    bootstrap = _build_workspace_bootstrap(working_directory, command)

    assert "cp -a /opt/agentsinc/frontend/node_modules /tmp/agentsinc-workspace/frontend/node_modules" in bootstrap
    assert "ln -s /opt/agentsinc/frontend/node_modules" not in bootstrap
    assert "cd /tmp/agentsinc-workspace/frontend; npm run build" in bootstrap


def test_python_suite_does_not_copy_frontend_dependencies() -> None:
    from app.sandbox import TEST_SUITES, _build_workspace_bootstrap

    working_directory, command = TEST_SUITES["python-tests"]
    bootstrap = _build_workspace_bootstrap(working_directory, command)

    assert "cp -a /opt/agentsinc/frontend/node_modules" not in bootstrap
