from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .workspace import workspace_root


TEST_SUITES: dict[str, tuple[str, str]] = {
    "python-tests": (
        "backend",
        "PYTHONPATH=/tmp/agentsinc-workspace/backend python3 -m pytest -q -p no:cacheprovider",
    ),
    "python-syntax": (
        ".",
        "python3 -c \"import ast,pathlib,sys; files=list(pathlib.Path('/tmp/agentsinc-workspace/backend').rglob('*.py')); "
        "[(ast.parse(p.read_text(encoding='utf-8'), filename=str(p))) for p in files]; "
        "print(f'Parsed {len(files)} Python files')\"",
    ),
    "frontend-typecheck": (
        "frontend",
        "npm run typecheck",
    ),
    "frontend-build": (
        "frontend",
        "npm run build",
    ),
}


def get_sandbox_status() -> dict[str, Any]:
    """Check Docker daemon and configured image, not just the docker.exe path."""
    docker = shutil.which("docker")
    image = os.getenv("AGENTSINC_SANDBOX_IMAGE", "").strip()
    status: dict[str, Any] = {
        "available": False,
        "docker_cli_available": bool(docker),
        "docker_daemon_available": False,
        "image_configured": bool(image),
        "image_available": False,
        "image": image or None,
        "reason": None,
    }
    if not docker:
        status["reason"] = "Docker CLI is not available on the backend process PATH."
        return status
    if not image:
        status["reason"] = "AGENTSINC_SANDBOX_IMAGE is not configured."
        return status
    try:
        result = subprocess.run(
            [docker, "image", "inspect", image, "--format", "{{.Id}}"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except subprocess.TimeoutExpired:
        status["reason"] = "Docker image inspection timed out while contacting the engine."
        return status
    except OSError as exc:
        status["reason"] = f"Docker could not be started ({type(exc).__name__})."
        return status
    if result.returncode == 0 and result.stdout.strip():
        status.update({
            "available": True,
            "docker_daemon_available": True,
            "image_available": True,
        })
        return status
    error = (result.stderr or result.stdout or "").lower()
    daemon_unavailable = any(marker in error for marker in (
        "cannot connect to the docker daemon",
        "failed to connect to the docker api",
        "is the docker daemon running",
        "error during connect",
        "the system cannot find the file specified",
    ))
    status["docker_daemon_available"] = not daemon_unavailable
    status["reason"] = (
        "Docker Desktop engine is not reachable from the backend process."
        if daemon_unavailable
        else f"Configured sandbox image '{image}' is not available. Build it with backend/Dockerfile.sandbox."
    )
    return status


def _build_workspace_bootstrap(working_directory: str, command: str) -> str:
    """Copy source into tmpfs and keep frontend dependencies inside the Turbopack root.

    Turbopack refuses to resolve the Next.js package through a node_modules symlink
    whose target lives outside the detected workspace root. A real copy into the
    disposable tmpfs workspace keeps dependency resolution hermetic while the
    original repository mount remains read-only.
    """
    bootstrap = (
        "set -eu; "
        "mkdir -p /tmp/agentsinc-workspace; "
        "tar -C /source "
        "--exclude=.git --exclude=.venv --exclude=__pycache__ "
        "--exclude=frontend/node_modules --exclude=frontend/.next "
        "-cf - . | tar -xf - -C /tmp/agentsinc-workspace; "
    )
    if working_directory == "frontend":
        bootstrap += (
            "if [ -d /opt/agentsinc/frontend/node_modules ] "
            "&& [ ! -e /tmp/agentsinc-workspace/frontend/node_modules ]; "
            "then cp -a /opt/agentsinc/frontend/node_modules "
            "/tmp/agentsinc-workspace/frontend/node_modules; fi; "
        )
    return bootstrap + "cd /tmp/agentsinc-workspace/" + working_directory + "; " + command


def run_test_suite(suite: str) -> dict[str, Any]:
    """Run a fixed test suite in a network-isolated, resource-limited Docker container."""
    if suite not in TEST_SUITES:
        raise ValueError(f"Unsupported test suite. Choose one of: {', '.join(sorted(TEST_SUITES))}.")
    docker = shutil.which("docker")
    if not docker:
        return {
            "status": "not_run",
            "suite": suite,
            "reason": "Docker is not installed or not available on PATH; no host-shell fallback is used.",
        }
    image = os.getenv("AGENTSINC_SANDBOX_IMAGE", "").strip()
    if not image:
        return {
            "status": "not_run",
            "suite": suite,
            "reason": "AGENTSINC_SANDBOX_IMAGE is not configured. Build the local test image using backend/Dockerfile.sandbox.",
        }

    source = workspace_root().resolve(strict=True)
    working_directory, command = TEST_SUITES[suite]
    bootstrap = _build_workspace_bootstrap(working_directory, command)
    args = [
        docker, "run", "--rm",
        "--network", "none",
        "--memory", "4g",
        "--cpus", "2",
        "--pids-limit", "128",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--read-only",
        "--tmpfs", "/tmp:rw,nosuid,nodev,size=3g",
        "-e", "PYTHONDONTWRITEBYTECODE=1",
        "-e", "PYTEST_ADDOPTS=-p no:cacheprovider",
        "-v", f"{source.as_posix()}:/source:ro",
        "-w", "/tmp",
        image,
        "sh", "-lc", bootstrap,
    ]
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"status": "timed_out", "suite": suite, "timeout_seconds": 900}
    except OSError as exc:
        return {"status": "not_run", "suite": suite, "reason": f"Docker could not be started: {type(exc).__name__}"}

    return {
        "status": "passed" if result.returncode == 0 else "failed",
        "suite": suite,
        "exit_code": result.returncode,
        "stdout": result.stdout[-10_000:],
        "stderr": result.stderr[-10_000:],
        "network": "disabled",
        "workspace_mount": "read-only; tests execute on a disposable tmpfs copy",
        "resource_limits": {"memory": "4g", "cpus": 2, "pids": 128},
    }
