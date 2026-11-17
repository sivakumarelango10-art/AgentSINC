from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from .redaction import redact_secrets
from .workspace import WorkspaceError, workspace_root


WRITABLE_ROOTS = (
    PurePosixPath("backend/app"),
    PurePosixPath("backend/tests"),
    PurePosixPath("frontend/src"),
    PurePosixPath("docs"),
)
WRITABLE_SUFFIXES = {".py", ".ts", ".tsx", ".css", ".md", ".json", ".svg", ".html"}
MAX_AGENT_FILE_BYTES = 192_000


def write_agent_file(relative_path: str, content: str) -> dict[str, Any]:
    """Apply a founder-approved code edit inside the configured workspace.

    Writes are restricted to source, tests and documentation. Secrets, config,
    dependency manifests, lockfiles, VCS metadata and symlink paths are refused.
    """
    raw_path = str(relative_path or "").strip()
    if not raw_path:
        raise WorkspaceError("A relative path is required.")
    windows_path = PureWindowsPath(raw_path)
    normalized = raw_path.replace("\\", "/")
    relative = PurePosixPath(normalized)
    if (
        windows_path.is_absolute()
        or windows_path.drive
        or relative.is_absolute()
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise WorkspaceError("Absolute paths and parent-directory traversal are not allowed.")

    if not any(relative == root or root in relative.parents for root in WRITABLE_ROOTS):
        raise WorkspaceError("Agent writes are limited to backend/app, backend/tests, frontend/src and docs.")
    if relative.suffix.lower() not in WRITABLE_SUFFIXES:
        raise WorkspaceError("This file type is not writable by an agent.")
    if relative.name.lower() in {".env", ".env.local", "credentials.json", "secrets.json"}:
        raise WorkspaceError("Secret and environment files cannot be modified by agents.")
    if relative.name.lower().endswith((".lock", ".map")) or relative.name.lower() in {
        "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "requirements.txt"
    }:
        raise WorkspaceError("Dependency and build configuration changes require a separate founder-managed change.")

    text = str(content or "")
    encoded = text.encode("utf-8")
    if not text.strip():
        raise WorkspaceError("Empty file content is not accepted.")
    if len(encoded) > MAX_AGENT_FILE_BYTES:
        raise WorkspaceError("The proposed file exceeds the 192 KB write limit.")
    if redact_secrets(text) != text:
        raise WorkspaceError("The proposed content contains a credential-like value and was blocked.")

    root = workspace_root().resolve(strict=True)
    target = root.joinpath(*relative.parts)
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise WorkspaceError("Symbolic link paths cannot be written.")
    try:
        parent = target.parent.resolve(strict=True)
        parent.relative_to(root)
    except (OSError, ValueError) as exc:
        raise WorkspaceError("The destination directory must already exist inside the workspace.") from exc
    if not parent.is_dir():
        raise WorkspaceError("The destination parent is not a directory.")
    if target.exists():
        if target.is_symlink() or not target.is_file():
            raise WorkspaceError("Only regular files can be replaced.")
        try:
            target.resolve(strict=True).relative_to(root)
        except (OSError, ValueError) as exc:
            raise WorkspaceError("The destination resolves outside the workspace.") from exc
    elif target.parent != parent:
        raise WorkspaceError("Invalid destination parent.")

    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=".agentsinc-write-",
            suffix=".tmp",
            dir=str(parent),
            delete=False,
        ) as temporary:
            temporary.write(encoded)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_name = temporary.name
        os.replace(temporary_name, target)
    except OSError as exc:
        if temporary_name:
            try:
                Path(temporary_name).unlink(missing_ok=True)
            except OSError:
                pass
        raise WorkspaceError("The approved file write failed.") from exc

    return {
        "status": "written",
        "path": relative.as_posix(),
        "bytes_written": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }
