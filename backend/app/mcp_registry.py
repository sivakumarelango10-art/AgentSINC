from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib.parse import urlparse


ROLE_IDS = {"developer", "designer", "researcher", "tester"}
STDIO_COMMANDS = {"python", "python3", "node", "npx", "uv", "docker"}


class MCPRegistryError(RuntimeError):
    pass


def load_mcp_config() -> list[dict[str, Any]]:
    """Load only founder-configured MCP servers; never infer or launch unknown servers."""
    raw = os.getenv("AGENTSINC_MCP_SERVERS_JSON", "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MCPRegistryError("AGENTSINC_MCP_SERVERS_JSON is not valid JSON.") from exc
    if not isinstance(parsed, list) or len(parsed) > 10:
        raise MCPRegistryError("MCP configuration must be an array with at most 10 servers.")
    validated = [_validate_server(item) for item in parsed]
    names = [item["name"] for item in validated]
    if len(names) != len(set(names)):
        raise MCPRegistryError("MCP server names must be unique.")
    return validated


def _expand_env_value(value: str) -> str:
    match = re.fullmatch(r"\$\{([A-Z][A-Z0-9_]*)\}", value)
    if not match:
        return value
    name = match.group(1)
    resolved = os.getenv(name)
    if resolved is None:
        raise MCPRegistryError(f"Required MCP environment variable {name} is not set.")
    return resolved


def _validate_server(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MCPRegistryError("Every MCP server entry must be an object.")
    name = str(value.get("name") or "").strip().lower()
    if not re.fullmatch(r"[a-z][a-z0-9_-]{1,39}", name):
        raise MCPRegistryError("MCP server names must use 2-40 lowercase letters, numbers, '_' or '-'.")
    transport = value.get("transport")
    if transport not in {"stdio", "http"}:
        raise MCPRegistryError(f"MCP server {name} must use stdio or http transport.")
    roles = value.get("roles", [])
    allow_tools = value.get("allow_tools", [])
    read_only_tools = value.get("read_only_tools", [])
    if not isinstance(roles, list) or not set(roles).issubset(ROLE_IDS):
        raise MCPRegistryError(f"MCP server {name} contains an invalid agent role.")
    if not isinstance(allow_tools, list) or not allow_tools or len(allow_tools) > 100:
        raise MCPRegistryError(f"MCP server {name} needs an explicit allow_tools list.")
    if not all(isinstance(tool, str) and tool for tool in allow_tools):
        raise MCPRegistryError(f"MCP server {name} has an invalid allowed tool name.")
    if not isinstance(read_only_tools, list) or not set(read_only_tools).issubset(set(allow_tools)):
        raise MCPRegistryError(f"MCP server {name} read_only_tools must be a subset of allow_tools.")

    result: dict[str, Any] = {
        "name": name,
        "transport": transport,
        "roles": roles,
        "allow_tools": allow_tools,
        "read_only_tools": read_only_tools,
    }
    if transport == "stdio":
        command = str(value.get("command") or "").strip()
        if command not in STDIO_COMMANDS:
            raise MCPRegistryError(
                f"MCP server {name} stdio command must be one of {', '.join(sorted(STDIO_COMMANDS))}."
            )
        args = value.get("args", [])
        env = value.get("env", {})
        if not isinstance(args, list) or len(args) > 40 or not all(isinstance(arg, str) for arg in args):
            raise MCPRegistryError(f"MCP server {name} args must be a string array of at most 40 entries.")
        if not isinstance(env, dict) or len(env) > 30:
            raise MCPRegistryError(f"MCP server {name} env must be an object with at most 30 entries.")
        result["command"] = command
        result["args"] = args
        result["env"] = {
            str(key): _expand_env_value(str(item))
            for key, item in env.items()
            if re.fullmatch(r"[A-Z][A-Z0-9_]{1,79}", str(key))
        }
    else:
        url = str(value.get("url") or "").strip()
        parsed = urlparse(url)
        local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if not (parsed.scheme == "https" or local_http) or not parsed.netloc or parsed.username or parsed.password:
            raise MCPRegistryError(f"MCP server {name} must use HTTPS or a loopback-only HTTP URL.")
        result["url"] = url
    return result


def configured_mcp_server_count() -> int:
    try:
        return len(load_mcp_config())
    except MCPRegistryError:
        return 0


class MCPRegistry:
    def __init__(self) -> None:
        self.servers = load_mcp_config()

    def _target(self, config: dict[str, Any]):
        if config["transport"] == "http":
            return config["url"]
        from mcp import StdioServerParameters
        return StdioServerParameters(
            command=config["command"],
            args=config["args"],
            env=config["env"],
        )

    async def discover(self, agent_id: str) -> list[dict[str, Any]]:
        try:
            from mcp import Client
        except ImportError as exc:
            if self.servers:
                raise MCPRegistryError("Install the MCP SDK with: pip install 'mcp>=2,<3'.") from exc
            return []

        discovered: list[dict[str, Any]] = []
        for config in self.servers:
            if agent_id not in config["roles"]:
                continue
            try:
                async with Client(self._target(config)) as client:
                    response = await client.list_tools()
                    for item in response.tools:
                        if item.name not in config["allow_tools"]:
                            continue
                        schema = getattr(item, "inputSchema", None) or {"type": "object", "properties": {}}
                        discovered.append({
                            "name": f"mcp.{config['name']}.{item.name}",
                            "description": str(getattr(item, "description", "") or "")[:1200],
                            "input_schema": schema,
                            "server_name": config["name"],
                            "tool_name": item.name,
                            "read_only": item.name in config["read_only_tools"],
                        })
            except Exception as exc:
                discovered.append({
                    "name": f"mcp.{config['name']}.__connection_error__",
                    "description": f"Configured MCP server unavailable ({type(exc).__name__}).",
                    "unavailable": True,
                })
        return discovered

    async def call_tool(
        self,
        agent_id: str,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        config = next((item for item in self.servers if item["name"] == server_name), None)
        if not config or agent_id not in config["roles"] or tool_name not in config["allow_tools"]:
            raise MCPRegistryError("The requested MCP tool is not allowlisted for this agent.")
        try:
            from mcp import Client
        except ImportError as exc:
            raise MCPRegistryError("Install the MCP SDK with: pip install 'mcp>=2,<3'.") from exc

        async with Client(self._target(config)) as client:
            response = await client.call_tool(tool_name, arguments)
        if getattr(response, "isError", False):
            raise MCPRegistryError(f"MCP tool {server_name}.{tool_name} reported an error.")
        structured = getattr(response, "structuredContent", None)
        if structured is None:
            structured = getattr(response, "structured_content", None)
        if structured is not None:
            return {"server": server_name, "tool": tool_name, "structured": structured}
        text_parts = []
        for part in (getattr(response, "content", None) or []):
            value = getattr(part, "text", None)
            if value:
                text_parts.append(str(value))
        return {"server": server_name, "tool": tool_name, "text": "\n".join(text_parts)[:12000]}
