from __future__ import annotations

import json

import pytest

from app.mcp_registry import MCPRegistry, MCPRegistryError, allowed_tools_for_role, load_mcp_config


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



def test_mcp_registry_limits_github_write_tools_to_developer_role(monkeypatch) -> None:
    monkeypatch.setenv(
        "AGENTSINC_MCP_SERVERS_JSON",
        json.dumps([{
            "name": "github",
            "transport": "stdio",
            "command": "docker",
            "args": ["run", "-i", "--rm", "ghcr.io/github/github-mcp-server"],
            "env": {},
            "roles": ["developer", "tester"],
            "allow_tools": ["get_file_contents", "create_branch", "push_files", "create_pull_request"],
            "read_only_tools": ["get_file_contents"],
            "role_allow_tools": {
                "developer": ["get_file_contents", "create_branch", "push_files", "create_pull_request"],
                "tester": ["get_file_contents"],
            },
        }]),
    )
    config = load_mcp_config()[0]
    assert allowed_tools_for_role(config, "developer") == [
        "get_file_contents", "create_branch", "push_files", "create_pull_request"
    ]
    assert allowed_tools_for_role(config, "tester") == ["get_file_contents"]


def test_mcp_registry_rejects_role_allowlist_for_unassigned_or_unknown_tool(monkeypatch) -> None:
    invalid_role = {
        "name": "github", "transport": "stdio", "command": "docker", "args": [],
        "roles": ["developer"], "allow_tools": ["get_file_contents"],
        "role_allow_tools": {"tester": ["get_file_contents"]},
    }
    monkeypatch.setenv("AGENTSINC_MCP_SERVERS_JSON", json.dumps([invalid_role]))
    with pytest.raises(MCPRegistryError, match="unassigned"):
        load_mcp_config()

    invalid_tool = {
        "name": "github", "transport": "stdio", "command": "docker", "args": [],
        "roles": ["developer"], "allow_tools": ["get_file_contents"],
        "role_allow_tools": {"developer": ["push_files"]},
    }
    monkeypatch.setenv("AGENTSINC_MCP_SERVERS_JSON", json.dumps([invalid_tool]))
    with pytest.raises(MCPRegistryError, match="subset of allow_tools"):
        load_mcp_config()


def test_stdio_mcp_server_inherits_parent_path_and_explicit_secrets(monkeypatch) -> None:
    monkeypatch.setenv("PATH", "C:\\Tools\\Docker;C:\\Windows\\System32")
    monkeypatch.setenv("MCP_PARENT_TEST", "inherited-value")
    monkeypatch.setenv(
        "AGENTSINC_MCP_SERVERS_JSON",
        json.dumps([{
            "name": "github",
            "transport": "stdio",
            "command": "docker",
            "args": ["run", "-i", "--rm", "ghcr.io/github/github-mcp-server"],
            "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "${MCP_PARENT_TEST}"},
            "roles": ["developer"],
            "allow_tools": ["get_file_contents"],
        }]),
    )
    config = load_mcp_config()[0]
    target = MCPRegistry()._target(config)
    assert target.env["PATH"] == "C:\\Tools\\Docker;C:\\Windows\\System32"
    assert target.env["MCP_PARENT_TEST"] == "inherited-value"
    assert target.env["GITHUB_PERSONAL_ACCESS_TOKEN"] == "inherited-value"
