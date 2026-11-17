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
