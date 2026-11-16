from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Iterable

MAX_INDEX_FILES = 1600
MAX_FILE_BYTES = 128_000
MAX_CONTEXT_CHARS = 22_000
ALLOWED_SUFFIXES = {
    ".py", ".pyi", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".json", ".md", ".mdx", ".yml", ".yaml", ".toml", ".ini",
    ".css", ".scss", ".html", ".sql", ".ps1", ".sh", ".txt",
    ".java", ".go", ".rs", ".c", ".h", ".cpp", ".hpp",
}
IGNORED_DIRS = {
    ".git", ".next", ".venv", "venv", "node_modules", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build",
    "out", ".turbo", ".vercel", "coverage", "playwright-report",
    "test-results", "site-packages", "vendor",
}
SENSITIVE_NAMES = {".env", ".npmrc", ".pypirc", "id_rsa", "id_ed25519", "credentials.json", "secrets.json"}
SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".sqlite", ".sqlite3", ".db"}
STOP_WORDS = {
    "the", "and", "for", "with", "from", "that", "this", "into", "your",
    "our", "you", "are", "was", "were", "will", "would", "could", "should",
    "about", "please", "make", "build", "create", "prepare", "current",
    "actual", "real", "agent", "agents", "sinc", "agentsinc", "task",
    "mission", "project", "work", "working", "using", "use", "based",
    "what", "where", "when", "which", "their", "them", "they", "have",
    "has", "had", "not", "only", "also", "all", "any", "how", "can",
}


SECRET_ASSIGNMENT = re.compile(
    r"""(?im)^([ \\t]*(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|secret|password|passwd|authorization)[ \\t]*[:=][ \\t]*)(?:"[^"\\r\\n]*"|'[^'\\r\\n]*'|[^\\s#]+)"""
)
JSON_SECRET_ASSIGNMENT = re.compile(
    r"""(?i)(["'](?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|secret|password|authorization)["'][ \\t]*:[ \\t]*)(["'])[^"']*\\2"""
)
KNOWN_TOKEN = re.compile(
    r"(?i)\\b(?:github_pat_|ghp_|gho_|ghu_|ghs_|ghr_|sk_live_|sk_test_|xox[baprs]-)[A-Za-z0-9_-]{12,}\\b"
)
BEARER_TOKEN = re.compile(r"(?i)\\bBearer[ \\t]+[A-Za-z0-9._~+/-]+=*")
PRIVATE_KEY_BLOCK = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----.*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    re.DOTALL,
)


def redact_sensitive_text(content: str) -> str:
    safe = PRIVATE_KEY_BLOCK.sub("[REDACTED PRIVATE KEY]", content)
    safe = KNOWN_TOKEN.sub("[REDACTED TOKEN]", safe)
    safe = BEARER_TOKEN.sub("Bearer [REDACTED TOKEN]", safe)
    safe = SECRET_ASSIGNMENT.sub(r"\\1[REDACTED]", safe)
    safe = JSON_SECRET_ASSIGNMENT.sub(r'\\1"[REDACTED]"', safe)
    safe = re.sub(r"\\bAKIA[0-9A-Z]{16}\\b", "[REDACTED ACCESS KEY]", safe)
    return safe


class WorkspaceError(ValueError):
    """Raised when a workspace path is missing or outside the configured root."""


@dataclass(frozen=True)
class WorkspaceContext:
    text: str
    files: list[str]


def workspace_root() -> Path:
    configured = os.getenv("AGENTSINC_WORKSPACE_ROOT")
    root = Path(configured).expanduser() if configured else Path(__file__).resolve().parents[2]
    try:
        resolved = root.resolve(strict=True)
    except FileNotFoundError as exc:
        raise WorkspaceError("The configured AgentSINC workspace directory does not exist.") from exc
    if not resolved.is_dir():
        raise WorkspaceError("The configured AgentSINC workspace path is not a directory.")
    return resolved


def _is_sensitive(relative: Path) -> bool:
    name = relative.name.lower()
    if name in SENSITIVE_NAMES or name.startswith(".env."):
        return True
    if relative.suffix.lower() in SENSITIVE_SUFFIXES:
        return True
    if any(part.lower() in {"secrets", "secret", "private", "credentials"} for part in relative.parts[:-1]):
        return True
    return False


def _is_ignored(relative: Path) -> bool:
    lowered = [part.lower() for part in relative.parts]
    if any(part in IGNORED_DIRS for part in lowered[:-1]):
        return True
    if any(part.startswith(".") and part not in {".github"} for part in relative.parts[:-1]):
        return True
    return _is_sensitive(relative)


def safe_file_path(relative_path: str) -> Path:
    raw = relative_path.strip()
    if not raw:
        raise WorkspaceError("A relative workspace path is required.")
    normalized = raw.replace("\\", "/")
    windows_path = PureWindowsPath(raw)
    candidate_part = Path(normalized)
    if windows_path.is_absolute() or windows_path.drive or candidate_part.is_absolute() or ".." in candidate_part.parts:
        raise WorkspaceError("Absolute paths and parent-directory traversal are not allowed.")

    root = workspace_root()
    candidate = root / candidate_part
    cursor = root
    for part in candidate_part.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise WorkspaceError("Symbolic links are excluded from workspace inspection.")
    try:
        resolved = candidate.resolve(strict=True)
        relative = resolved.relative_to(root)
    except (FileNotFoundError, ValueError, OSError) as exc:
        raise WorkspaceError("The requested file does not exist inside the configured workspace.") from exc

    if resolved == root or not resolved.is_file():
        raise WorkspaceError("Only existing workspace files can be read.")
    if candidate.is_symlink() or _is_ignored(relative):
        raise WorkspaceError("This file is excluded from AgentSINC workspace inspection.")
    if resolved.suffix.lower() not in ALLOWED_SUFFIXES:
        raise WorkspaceError("This file type is not available for workspace inspection.")
    try:
        if resolved.stat().st_size > MAX_FILE_BYTES:
            raise WorkspaceError("This file is too large for safe inline inspection.")
    except OSError as exc:
        raise WorkspaceError("The requested file could not be inspected.") from exc
    return resolved


def iter_workspace_files(max_files: int = MAX_INDEX_FILES) -> Iterable[tuple[str, Path]]:
    root = workspace_root()
    count = 0
    for current, directories, names in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        relative_dir = current_path.relative_to(root)
        directories[:] = [
            name for name in directories
            if name.lower() not in IGNORED_DIRS
            and not (current_path / name).is_symlink()
            and not name.startswith(".")
        ]
        if relative_dir.parts and _is_ignored(relative_dir / "placeholder.txt"):
            directories[:] = []
            continue

        for name in names:
            path = current_path / name
            try:
                relative = path.relative_to(root)
                if path.is_symlink() or _is_ignored(relative):
                    continue
                if path.suffix.lower() not in ALLOWED_SUFFIXES:
                    continue
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield relative.as_posix(), path
            count += 1
            if count >= max(1, min(max_files, MAX_INDEX_FILES)):
                return


def list_workspace_files(limit: int = 200) -> list[str]:
    bounded = max(1, min(limit, 500))
    return [relative for relative, _ in iter_workspace_files(max_files=bounded)]


def read_workspace_file(relative_path: str, max_chars: int = 16_000) -> str:
    path = safe_file_path(relative_path)
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise WorkspaceError("The requested file could not be read.") from exc
    return redact_sensitive_text(content[:max(500, min(max_chars, 24_000))])


def search_workspace(query: str, max_results: int = 12) -> list[dict[str, str | int]]:
    tokens = {
        token for token in re.findall(r"[a-zA-Z0-9_./-]{3,}", query.lower())
        if token not in STOP_WORDS
    }
    if not tokens:
        return []

    results: list[dict[str, str | int]] = []
    for relative, path in iter_workspace_files():
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        content = redact_sensitive_text(content)
        lower = content.lower()
        path_lower = relative.lower()
        score = sum(4 for token in tokens if token in path_lower)
        score += sum(min(lower.count(token), 8) for token in tokens)
        if score < 2:
            continue
        matched = next((token for token in sorted(tokens, key=len, reverse=True) if token in lower), None)
        snippet = ""
        if matched:
            index = lower.find(matched)
            start = max(0, index - 240)
            end = min(len(content), index + len(matched) + 420)
            snippet = " ".join(content[start:end].split())
        results.append({"path": relative, "score": score, "snippet": snippet[:700]})

    results.sort(key=lambda item: (-int(item["score"]), str(item["path"])))
    return results[:max(1, min(max_results, 30))]


def build_workspace_context(query: str) -> WorkspaceContext:
    root = workspace_root()
    files = list(iter_workspace_files())
    by_path = {relative: path for relative, path in files}
    selected: list[str] = []

    preferred = [
        "README.md", "docs/PHASES.md", "docs/ARCHITECTURE.md",
        "docs/3D_OFFICE_DESIGN.md", "backend/README.md", "frontend/README.md",
        "package.json", "frontend/package.json", "backend/requirements.txt",
        "backend/app/main.py", "backend/app/db.py", "backend/app/worker.py",
    ]
    for relative in preferred:
        if relative in by_path and relative not in selected:
            selected.append(relative)

    for item in search_workspace(query, max_results=24):
        relative = str(item["path"])
        if relative in by_path and relative not in selected:
            selected.append(relative)

    sections: list[str] = []
    included: list[str] = []
    remaining = MAX_CONTEXT_CHARS
    for relative in selected:
        if remaining < 900:
            break
        try:
            content = by_path[relative].read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        per_file_limit = 5_000 if relative.endswith((".md", ".json", ".yml", ".yaml", ".toml", ".txt")) else 3_500
        if relative in {"backend/app/main.py", "backend/app/worker.py", "backend/app/db.py"}:
            per_file_limit = 6_000
        content = redact_sensitive_text(content[:min(per_file_limit, remaining - 300)])
        if not content.strip():
            continue
        section = f"### FILE: {relative}\n[BEGIN FILE CONTENT]\n{content}\n[END FILE CONTENT]"
        if len(section) > remaining:
            section = section[:remaining]
        sections.append(section)
        included.append(relative)
        remaining -= len(section) + 2

    if not sections:
        text = "No readable project source files were found in the configured workspace. Do not claim to have inspected the codebase."
    else:
        text = (
            f"Configured workspace: {root.name}\n"
            f"Read-only source files supplied ({len(included)} files): {', '.join(included)}\n\n"
            + "\n\n".join(sections)
        )
    return WorkspaceContext(text=text, files=included)


def workspace_summary() -> dict[str, object]:
    root = workspace_root()
    files = list_workspace_files(limit=MAX_INDEX_FILES)
    return {
        "available": True,
        "root_name": root.name,
        "file_count": len(files),
        "read_only": True,
        "ignored_areas": sorted(IGNORED_DIRS),
        "sensitive_files_excluded": True,
    }
