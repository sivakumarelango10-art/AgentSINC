# GitHub development workflow

## What the pipeline does

For a founder request that asks for code implementation and a GitHub push or pull request, the Team Lead prepares sequential missions:

1. **Developer — implementation:** inspect the actual local workspace and propose source changes. Each file write waits for founder approval.
2. **QA — validation:** run the relevant fixed test suites inside the configured Docker sandbox and report the real status and exit code.
3. **Developer — release:** use explicitly allowlisted GitHub MCP tools to create a feature branch, push the reviewed files, then open a pull request.

The worker processes queued specialist tasks in insertion order. Team Lead synthesis receives the persisted tool-event evidence from all three stages.

The harness enforces the critical gates:
- GitHub `push_files` and `create_or_update_file` are rejected until the QA Agent has a `tests.run` event with status `PASSED` and exit code `0` in the same orchestration.
- `create_pull_request` is rejected until a successful feature-branch push is recorded and the PR head matches that branch.
- Writes to `main`, `master`, `production`, `prod` or `release` are blocked.
- Every remote mutation requires founder approval.
- `merge_pull_request` is always denied to agents. A founder merges manually.

If the GitHub MCP server is not configured or unavailable, the release stage reports the blocker instead of claiming that a push or PR happened.

## 1. Prepare Docker Desktop and a fine-grained token

Install and start Docker Desktop. The local GitHub MCP connection runs the official server image `ghcr.io/github/github-mcp-server`.

Create a GitHub fine-grained personal access token restricted to the AgentSINC repository. Grant only:
- **Contents: Read and write** (branch creation and file pushes).
- **Pull requests: Read and write** (PR creation and reading).
- **Metadata: Read-only** (repository metadata; normally included as a required permission).

GitHub recommends fine-grained tokens where possible. Treat the token like a password, keep it local, and set an expiration. Never paste it into an agent mission, source file, GitHub issue, or chat.

References:
- https://github.com/github/github-mcp-server
- https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens
- https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens

## 2. Configure backend/.env

Open `E:\AgentSINC\backend\.env` (create it from `.env.example` if needed) and add your token:

```dotenv
GITHUB_PERSONAL_ACCESS_TOKEN=YOUR_FINE_GRAINED_TOKEN
```

Then set the MCP registry to the official Docker server. This configuration gives Developer the branch/push/PR tools while QA receives only read-only tools:

```dotenv
AGENTSINC_MCP_SERVERS_JSON='[{"name":"github","transport":"stdio","command":"docker","args":["run","-i","--rm","-e","GITHUB_PERSONAL_ACCESS_TOKEN","-e","GITHUB_TOOLSETS=repos,pull_requests,users","ghcr.io/github/github-mcp-server"],"env":{"GITHUB_PERSONAL_ACCESS_TOKEN":"${GITHUB_PERSONAL_ACCESS_TOKEN}","GITHUB_TOOLSETS":"repos,pull_requests,users"},"roles":["developer","tester"],"allow_tools":["get_me","search_repositories","get_file_contents","list_branches","get_commit","list_pull_requests","pull_request_read","create_branch","push_files","create_pull_request"],"read_only_tools":["get_me","search_repositories","get_file_contents","list_branches","get_commit","list_pull_requests","pull_request_read"],"role_allow_tools":{"developer":["get_me","search_repositories","get_file_contents","list_branches","get_commit","list_pull_requests","pull_request_read","create_branch","push_files","create_pull_request"],"tester":["get_me","search_repositories","get_file_contents","list_branches","get_commit","list_pull_requests","pull_request_read"]}}]'
```

The registry inherits the backend process environment, so Docker can be resolved from your Windows PATH and the named token variable can be forwarded into the container. No token value is included in the JSON itself.

## 3. Restart and verify

Restart the FastAPI process and the AgentSINC worker so they reload `backend/.env`. Open **Settings → GitHub development pipeline**. The integration card should show:
- GitHub server connected.
- Developer tools include `create_branch`, `push_files` and `create_pull_request`.
- Tester tools are read-only.

If the card reports unavailable, check Docker Desktop is running, the token has access to AgentSINC, and the configured tool names match the official MCP server.

## 4. Test the release workflow

Ask the CEO/Team Lead to implement a small, low-risk change and open a pull request. The expected activity sequence is:

```text
Developer: inspect repository
Developer: propose source file write
Founder: approve exact file write
QA: run Docker test suites
Developer: create feature branch (founder approval)
Developer: push reviewed files (founder approval; QA pass required)
Developer: create pull request (founder approval; push required)
Team Lead: verify persisted tool events and consolidate the report
```

You can inspect each step in the agent inspector's execution trace, the Mission Board and the physical workstation monitor.

Do not enable the `merge_pull_request` tool in the allowlist. AgentSINC blocks merge operations at the harness regardless.
