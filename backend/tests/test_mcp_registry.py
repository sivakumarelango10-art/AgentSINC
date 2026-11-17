from __future__ import annotations

import json

import pytest

from app.mcp_registry import MCPRegistryError, load_mcp_config


def test_mcp_registry_requires_explicit_role_and_tool_allowlists(monkeypatch) -> None:
    monkeypatch.setenv(
        "AGENTSINC_MCP_SERVERS_JSON",
        json.dumps([{
            "name": "github",
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {},
            "roles": ["developer", "tester"],
            "allow_tools": ["search_repositories", "get_file_contents", "create_or_update_file"],
            "read_only_tools": ["search_repositories", "get_file_contents"],
        }]),
    )
    servers = load_mcp_config()
    assert len(servers) == 1
    assert servers[0]["name"] == "github"
    assert servers[0]["allow_tools"] == ["search_repositories", "get_file_contents", "create_or_update_file"]
    assert servers[0]["read_only_tools"] == ["search_repositories", "get_file_contents"]


@pytest.mark.parametrize(
    "server",
    [
        {"name": "github", "transport": "stdio", "command": "bash", "args": [], "roles": ["developer"], "allow_tools": ["x"]},
        {"name": "github", "transport": "stdio", "command": "npx", "args": [], "roles": ["ceo"], "allow_tools": ["x"]},
        {"name": "github", "transport": "stdio", "command": "npx", "args": [], "roles": ["developer"], "allow_tools": []},
        {"name": "github", "transport": "stdio", "command": "npx", "args": [], "roles": ["developer"], "allow_tools": ["x"], "read_only_tools": ["not-allowlisted"]},
        {"name": "github", "transport": "http", "url": "http://example.com/mcp", "roles": ["developer"], "allow_tools": ["x"]},
        {"name": "github", "transport": "http", "url": "https://user:pass@example.com/mcp", "roles": ["developer"], "allow_tools": ["x"]},
    ],
)
def test_mcp_registry_rejects_unsafe_or_ambiguous_server_config(monkeypatch, server) -> None:
    monkeypatch.setenv("AGENTSINC_MCP_SERVERS_JSON", json.dumps([server]))
    with pytest.raises(MCPRegistryError):
        load_mcp_config()


def test_mcp_registry_expands_only_named_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN_TEST", "not-a-real-token")
    monkeypatch.setenv(
        "AGENTSINC_MCP_SERVERS_JSON",
        json.dumps([{
            "name": "github",
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "server"],
            "env": {"TOKEN": "${GITHUB_TOKEN_TEST}"},
            "roles": ["developer"],
            "allow_tools": ["search_repositories"],
            "read_only_tools": ["search_repositories"],
        }]),
    )
    assert load_mcp_config()[0]["env"]["TOKEN"] == "not-a-real-token"
