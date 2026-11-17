from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Callable

import httpx

from .db import add_event, connect, create_tool_approval, get_tool_approval
from .mcp_registry import MCPRegistry, MCPRegistryError
from .redaction import redact_secrets
from .research import fetch_google_search_context
from .sandbox import run_test_suite
from .workspace import WorkspaceError, read_workspace_file, search_workspace


TOOL_SPECS: dict[str, dict[str, Any]] = {
    "repo.search": {
        "description": "Search the actual configured AgentSINC workspace. Returns matching relative paths and evidence snippets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 2, "maxLength": 240},
                "limit": {"type": "integer", "minimum": 1, "maximum": 12},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    "repo.read": {
        "description": "Read one existing, non-sensitive file from the configured workspace by relative path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "minLength": 1, "maxLength": 240},
                "max_chars": {"type": "integer", "minimum": 500, "maximum": 24000},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    "workspace.write_file": {
        "description": "Propose a real source-code or documentation file write. This always pauses for founder approval before touching the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "minLength": 1, "maxLength": 240},
                "content": {"type": "string", "minLength": 1, "maxLength": 192000},
                "summary": {"type": "string", "minLength": 8, "maxLength": 500},
            },
            "required": ["path", "content", "summary"],
            "additionalProperties": False,
        },
    },
    "tests.run": {
        "description": "Run one fixed test suite inside the local Docker sandbox. The container has no network, strict resource limits and a read-only source mount; source is copied to disposable tmpfs for execution.",
        "input_schema": {
            "type": "object",
            "properties": {
                "suite": {
                    "type": "string",
                    "enum": ["python-tests", "python-syntax", "frontend-typecheck", "frontend-build"],
                },
            },
            "required": ["suite"],
            "additionalProperties": False,
        },
    },
    "research.google_search": {
        "description": "Run genuine Google Search-grounded research for the Research Agent. Requires explicit founder opt-in and a Gemini API key.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "minLength": 10, "maxLength": 5000},
            },
            "required": ["question"],
            "additionalProperties": False,
        },
    },
}

ROLE_TOOLS = {
    "developer": ("repo.search", "repo.read", "workspace.write_file", "tests.run"),
    "designer": ("repo.search", "repo.read", "workspace.write_file", "tests.run"),
    "researcher": ("repo.search", "repo.read", "research.google_search"),
    "tester": ("repo.search", "repo.read", "tests.run"),
}


class HarnessCancelled(RuntimeError):
    """Raised when a founder cancels a task while the harness is waiting."""


class AgentHarness:
    """Role-scoped tool harness for one persisted mission."""

    def __init__(
        self,
        task: dict[str, Any],
        client: httpx.AsyncClient,
        progress: Callable[[int, str], None],
        cancelled: Callable[[], bool],
    ) -> None:
        self.task = task
        self.client = client
        self.progress = progress
        self.cancelled = cancelled
        self.registry: MCPRegistry | None = None
        self.registry_error: str | None = None
        self.mcp_tools: dict[str, dict[str, Any]] = {}

    async def discover_tools(self) -> list[dict[str, Any]]:
        agent_id = self.task["agent_id"]
        tools = [
            {
                "name": name,
                "description": TOOL_SPECS[name]["description"],
                "parameters": TOOL_SPECS[name]["input_schema"],
                "approval_required": name == "workspace.write_file",
            }
            for name in ROLE_TOOLS.get(agent_id, ())
        ]
        try:
            self.registry = MCPRegistry()
            discovered = await self.registry.discover(agent_id)
            for item in discovered:
                if item.get("unavailable") or item["name"].endswith(".__connection_error__"):
                    self.registry_error = item["description"]
                    continue
                self.mcp_tools[item["name"]] = item
                tools.append({
                    "name": item["name"],
                    "description": item["description"] or f"Call configured MCP tool {item['name']}.",
                    "parameters": item["input_schema"],
                    "approval_required": not item["read_only"],
                })
        except MCPRegistryError as exc:
            self.registry_error = str(exc)
        return tools

    def _record_tool_event(self, event_type: str, message: str) -> None:
        """Persist a compact, credential-redacted execution trace for this mission."""
        with connect() as connection:
            add_event(
                connection,
                self.task["agent_id"],
                self.task["id"],
                event_type,
                redact_secrets(message)[:1200],
            )
            connection.commit()

    def _related_tool_events(self) -> list[dict[str, Any]]:
        orchestration_id = self.task.get("orchestration_id")
        with connect() as connection:
            if orchestration_id:
                rows = connection.execute(
                    """SELECT e.agent_id, e.event_type, e.message, e.task_id
                    FROM events e LEFT JOIN tasks t ON t.id=e.task_id
                    WHERE e.task_id=? OR t.orchestration_id=?
                    ORDER BY e.id ASC LIMIT 250""",
                    (self.task["id"], orchestration_id),
                ).fetchall()
            else:
                rows = connection.execute(
                    """SELECT agent_id, event_type, message, task_id
                    FROM events WHERE task_id=? ORDER BY id ASC LIMIT 100""",
                    (self.task["id"],),
                ).fetchall()
        return [dict(row) for row in rows]

    def _has_required_qa_pass(self) -> bool:
        orchestration_id = self.task.get("orchestration_id")
        for event in self._related_tool_events():
            if event["event_type"] != "tool_completed" or not str(event["message"]).startswith("tests.run:"):
                continue
            if "PASSED; exit=0" not in str(event["message"]):
                continue
            if orchestration_id and event["agent_id"] == "tester":
                return True
            if not orchestration_id and event["task_id"] == self.task["id"]:
                return True
        return False

    def _latest_pushed_branch(self) -> str | None:
        for event in reversed(self._related_tool_events()):
            if event["event_type"] != "tool_completed":
                continue
            message = str(event["message"])
            if not re.match(r"mcp\\.[a-z0-9_-]+\\.(?:push_files|create_or_update_file):", message):
                continue
            match = re.search(r"""\\bbranch ['"]([^'"]+)['"]""", message, flags=re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _github_mutation_policy_error(self, tool_name: str, arguments: dict[str, Any]) -> str | None:
        if tool_name == "merge_pull_request":
            return "Pull request merging is disabled for agents. A founder must merge manually."
        if tool_name in {"push_files", "create_or_update_file"}:
            if not self._has_required_qa_pass():
                required = "the QA Agent's successful test run in this orchestration" if self.task.get("orchestration_id") else "a successful test run in this mission"
                return f"GitHub publishing is blocked until {required} is recorded (PASSED, exit code 0)."
            branch = str(arguments.get("branch") or "").strip()
            if not branch:
                return "GitHub source writes require an explicit feature branch."
            if branch.casefold() in {"main", "master", "production", "prod", "release"}:
                return f"Direct writes to protected/default branch '{branch}' are blocked. Use a feature branch."
            return None
        if tool_name == "create_pull_request":
            if not self._has_required_qa_pass():
                return "Opening a pull request is blocked until the required QA test run passes."
            pushed_branch = self._latest_pushed_branch()
            if not pushed_branch:
                return "Opening a pull request is blocked until a successful GitHub file push is recorded."
            head = str(arguments.get("head") or "").strip()
            base = str(arguments.get("base") or "").strip()
            head_branch = head.rsplit(":", 1)[-1]
            if not head or not base or head_branch != pushed_branch:
                return f"The pull request head must match the successfully pushed feature branch '{pushed_branch}'."
            if head_branch.casefold() == base.casefold():
                return "The pull request head and base branches must be different."
        return None

    def _tool_result_summary(self, name: str, arguments: dict[str, Any], output: str) -> str:
        clean = redact_secrets(str(output or "")).replace("\r", " ").replace("\n", " ")
        clean = re.sub(r"\s+", " ", clean).strip()

        if name == "tests.run":
            try:
                result = json.loads(output)
            except (TypeError, ValueError):
                result = {}
            suite = str(result.get("suite") or arguments.get("suite") or "test suite")
            status = str(result.get("status") or "unknown").upper()
            exit_code = result.get("exit_code")
            detail = str(result.get("stdout") or result.get("stderr") or "").strip()
            detail = re.sub(r"\s+", " ", redact_secrets(detail))
            return f"{suite}: {status}; exit={exit_code if exit_code is not None else 'n/a'}; {detail[-280:]}".strip()

        if name == "research.google_search":
            urls = list(dict.fromkeys(re.findall(r"""https?://[^\s\])>"']+""", clean)))
            if urls:
                return f"Google Search returned {len(urls)} source URL(s): " + " | ".join(urls[:3])
            return clean[:560] or "Research tool returned no text."

        if name == "workspace.write_file":
            try:
                result = json.loads(output)
            except (TypeError, ValueError):
                result = {}
            if result.get("status") == "written":
                return (
                    f"Wrote {result.get('path', 'source file')} "
                    f"({result.get('bytes_written', 0)} bytes; SHA-256 {str(result.get('sha256', ''))[:16]}…)."
                )
            return clean[:560] or "File change is awaiting founder approval."

        if name == "repo.search":
            try:
                result = json.loads(output)
            except (TypeError, ValueError):
                result = {}
            matches = result.get("matches") if isinstance(result, dict) else None
            if isinstance(matches, list):
                found_paths = [str(item.get("path")) for item in matches[:3] if isinstance(item, dict) and item.get("path")]
                return f"Repository search found {len(matches)} match(es)" + (": " + ", ".join(found_paths) if found_paths else ".")
            return clean[:560]

        if name == "repo.read":
            path = str(arguments.get("path") or "workspace file")
            return f"Read {path} ({len(output)} characters)."

        if name.startswith("mcp."):
            tool_name = name.rsplit(".", 1)[-1]
            urls = list(dict.fromkeys(re.findall(r"""https?://[^\s\])>"']+""", clean)))
            if tool_name == "push_files":
                files = arguments.get("files") if isinstance(arguments.get("files"), list) else []
                branch = str(arguments.get("branch") or "unknown")
                summary = f"Pushed {len(files)} file(s) to branch '{branch}'"
                sha_match = re.search(r"""["'](?:sha|oid)["']\s*:\s*["']([0-9a-f]{7,40})""", clean, re.IGNORECASE)
                if sha_match:
                    summary += f" (commit {sha_match.group(1)[:12]})"
                if urls:
                    summary += f": {urls[0]}"
                return summary + "."
            if tool_name == "create_or_update_file":
                branch = str(arguments.get("branch") or "unknown")
                path = str(arguments.get("path") or "source file")
                return f"Updated {path} on feature branch '{branch}'" + (f": {urls[0]}" if urls else ".")
            if tool_name == "create_branch":
                branch = str(arguments.get("branch") or "requested branch")
                return f"Created GitHub branch '{branch}'" + (f": {urls[0]}" if urls else ".")
            if tool_name == "create_pull_request":
                number = re.search(r"""["']number["']\s*:\s*(\d+)""", clean)
                if not number and urls:
                    number = re.search(r"/pull/(\d+)", urls[0])
                label = f"Created GitHub pull request #{number.group(1)}" if number else "Created GitHub pull request"
                return label + (f": {urls[0]}" if urls else f" · {clean[:220]}")
            return f"{name} returned {len(output)} character(s): " + (urls[0] if urls else clean[:300])

        return clean[:560] or f"{name} returned an empty result."

    async def execute_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Log each actual tool invocation and its real bounded result."""
        if self.cancelled():
            raise HarnessCancelled("Mission cancelled before tool execution.")
        safe_name = str(name or "unknown")[:120]
        self._record_tool_event("tool_started", f"Started tool: {safe_name}.")
        try:
            output = await self._execute_tool_impl(name, arguments)
        except Exception as exc:
            self._record_tool_event(
                "tool_failed",
                f"{safe_name} failed before returning a result ({type(exc).__name__}).",
            )
            raise

        lower = output.lower()
        event_type = "tool_completed"
        if "waiting for founder approval" in lower or ("approval request" in lower and "visible" in lower):
            event_type = "tool_awaiting_approval"
        elif any(token in lower for token in (
            "tool execution was rejected", "tool execution failed", "external research request failed",
            "approved action failed", "founder rejected", "approval timed out", "not available to the", "not configured",
        )):
            event_type = "tool_failed"
        elif name == "tests.run":
            try:
                test_status = str(json.loads(output).get("status") or "").lower()
            except (TypeError, ValueError):
                test_status = ""
            if test_status in {"failed", "timed_out"}:
                event_type = "tool_failed"
            elif test_status == "not_run":
                event_type = "tool_blocked"

        self._record_tool_event(
            event_type,
            f"{safe_name}: {self._tool_result_summary(name, arguments, output)}",
        )
        return output

    async def _execute_tool_impl(self, name: str, arguments: dict[str, Any]) -> str:
        if self.cancelled():
            raise RuntimeError("Mission cancelled before tool execution.")
        if not isinstance(arguments, dict):
            return "Tool arguments must be a JSON object."

        try:
            if name == "repo.search":
                query = str(arguments.get("query") or "")
                results = search_workspace(query, int(arguments.get("limit", 8)))
                return json.dumps({"matches": results}, ensure_ascii=False)[:12000]

            if name == "repo.read":
                content = read_workspace_file(
                    str(arguments.get("path") or ""),
                    int(arguments.get("max_chars", 12000)),
                )
                return content[:24000]

            if name == "workspace.write_file":
                payload = {
                    "path": str(arguments.get("path") or ""),
                    "content": str(arguments.get("content") or ""),
                    "summary": str(arguments.get("summary") or ""),
                }
                return await self._request_approval(name, payload)

            if name == "tests.run":
                suite = str(arguments.get("suite") or "")
                result = await asyncio.to_thread(run_test_suite, suite)
                return json.dumps(result, ensure_ascii=False)[:16000]

            if name == "research.google_search":
                if self.task["agent_id"] != "researcher":
                    return "This research tool is available only to the Research Agent."
                result = await fetch_google_search_context(
                    self.client,
                    str(self.task["title"]),
                    str(arguments.get("question") or ""),
                )
                return result[:12000]

            item = self.mcp_tools.get(name)
            if item:
                if not self.registry:
                    return "The configured MCP registry is unavailable."
                if not item["read_only"]:
                    policy_error = self._github_mutation_policy_error(item["tool_name"], arguments)
                    if policy_error:
                        return f"Tool execution was rejected: {policy_error}"
                payload = {
                    "server_name": item["server_name"],
                    "tool_name": item["tool_name"],
                    "arguments": arguments,
                }
                if item["read_only"]:
                    result = await self.registry.call_tool(
                        self.task["agent_id"],
                        item["server_name"],
                        item["tool_name"],
                        arguments,
                    )
                    return json.dumps(result, ensure_ascii=False)[:12000]
                return await self._request_approval(name, payload)

            return f"Tool {name!r} is not available to the {self.task['agent_id']} agent."
        except HarnessCancelled:
            raise
        except (WorkspaceError, MCPRegistryError, ValueError, TypeError) as exc:
            return f"Tool execution was rejected: {exc}"
        except httpx.HTTPError as exc:
            return f"External research request failed ({type(exc).__name__})."
        except Exception as exc:
            return f"Tool execution failed ({type(exc).__name__})."

    async def _request_approval(self, tool_name: str, payload: dict[str, Any]) -> str:
        approval = create_tool_approval(
            self.task["id"],
            self.task["agent_id"],
            tool_name,
            payload,
        )
        approval_id = approval["id"]
        self._record_tool_event(
            "tool_awaiting_approval",
            f"Founder approval requested for {tool_name}; request {approval_id[:8]}.",
        )
        self.progress(78, f"Waiting for founder approval: {tool_name} ({approval_id[:8]}).")
        self.progress(78, f"Approval request {approval_id[:8]} is visible in the AgentSINC Approvals panel.")

        # The worker retains the mission context while the founder reviews the proposal.
        # No write or external mutation occurs in this process before approval.
        for _ in range(900):  # 30 minutes at a 2-second polling interval
            if self.cancelled():
                raise HarnessCancelled("Mission cancelled while waiting for founder approval.")
            current = get_tool_approval(approval_id)
            if not current:
                return "Approval request disappeared; the tool was not executed."
            if current["status"] == "approved":
                return current.get("result") or "Founder approved and the tool completed."
            if current["status"] == "rejected":
                return current.get("result") or "Founder rejected the proposed action."
            if current["status"] == "failed":
                return current.get("result") or "The approved tool action failed."
            await asyncio.sleep(2)

        return "Approval timed out after 30 minutes; the proposed action was not executed."
