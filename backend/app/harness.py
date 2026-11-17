from __future__ import annotations

import asyncio
import json
from typing import Any, Callable

import httpx

from .db import create_tool_approval, get_tool_approval
from .mcp_registry import MCPRegistry, MCPRegistryError
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

    async def execute_tool(self, name: str, arguments: dict[str, Any]) -> str:
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
