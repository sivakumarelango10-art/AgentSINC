# AgentSINC Agent Harness

The local worker runs specialist missions through an iterative Ollama tool loop. Tools are role-scoped:

| Agent | Default tools |
|---|---|
| Developer | repository search/read, approval-gated source writes, fixed Docker test suites |
| Designer | repository search/read, approval-gated frontend/CSS edits, fixed Docker test suites |
| Researcher | repository search/read and optional Google Search grounding |
| QA | repository search/read and fixed Docker test suites |

## Local setup

The harness is enabled by default. Keep the backend and worker local, with Ollama running.

Optional backend/.env settings:

```env
AGENTSINC_AGENT_HARNESS_ENABLED=true
AGENTSINC_SANDBOX_IMAGE=agentsinc-sandbox:local
AGENTSINC_MCP_SERVERS_JSON=
```

Build the fixed test image from the repository root:

```powershell
docker build -t agentsinc-sandbox:local -f backend/Dockerfile.sandbox .
```

The test runner starts a fresh container for each fixed suite. It disables networking, drops Linux capabilities, applies CPU/memory/PID limits, mounts source read-only, copies it to disposable tmpfs, and only runs a fixed test suite. It never falls back to running generated commands on the host.

## Source changes and approvals

An agent can propose a source/documentation edit. The exact path, content and summary are persisted in SQLite. The agent pauses until the founder approves or rejects it in the Approvals panel. Only then does the API apply the stored content using an atomic write. Writes are limited to:

- backend/app/
- backend/tests/
- frontend/src/
- docs/

Dependency manifests, lockfiles, environment files, credentials, absolute paths, traversal and symlinks are refused. Agent-authored writes do not run automatically just because the model requested them.

## MCP server configuration

AgentSINC never guesses, auto-installs or launches unknown MCP servers. Configure servers explicitly using AGENTSINC_MCP_SERVERS_JSON. Each entry must specify a unique server name, stdio or Streamable HTTP transport, a restricted stdio executable or HTTPS/loopback URL, an agent-role allowlist, explicit allow_tools, and a read_only_tools subset. All other tools are considered mutating and require founder approval.

Example only; check tool names against the MCP server's actual tools/list response before allowing them:

```json
[
  {
    "name": "github",
    "transport": "stdio",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {
      "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
    },
    "roles": ["developer", "tester"],
    "allow_tools": ["search_repositories", "get_file_contents", "create_or_update_file"],
    "read_only_tools": ["search_repositories", "get_file_contents"]
  }
]
```

Use environment-variable references for credentials. Do not paste secrets directly into JSON or commit them. MCP servers are started by the local worker only when a configured role discovers or invokes an allowed tool. A mutating call is re-authorized at execution time after founder approval.

## Current boundaries

- Google Search is real only for the Research Agent when explicitly enabled with a Gemini API key.
- GitHub repo creation, branch/PR operations, deployment and other external side effects require a GitHub MCP server or another explicit configured integration. They are not silently enabled by this local code.
- Test execution needs Docker and the sandbox image. If either is missing, the tool reports not_run; it does not pretend tests passed or run arbitrary host commands.
- Agent memory is local retrieval over completed work, not model-weight fine-tuning.
- ChatGPT-connected plugins are not automatically available to a separate local Python process. Configure local MCP endpoints/servers that expose the integrations AgentSINC needs.
