# AgentSINC local runtime

This is the first executable AgentSINC runtime. It is local-first and uses:

- FastAPI for a localhost-only API.
- SQLite for durable agent, mission and event history.
- Ollama for local model inference; no paid model API key is required.
- A separate Python worker that polls queued missions, writes progress, and publishes a heartbeat.

The 3D office is a client. Closing the browser does not stop the worker. The scene now reflects live agent state and includes separate four-seat discussion and eight-seat meeting rooms.

## Requirements

- Python 3.11 or newer.
- Ollama installed and running on this computer.
- At least one chat model installed in Ollama.
- Node.js is needed separately for the frontend.

No PostgreSQL, Redis, paid API, cloud VM or paid hosting is used by this local MVP.

## Install on Windows

From PowerShell:

    cd E:\AgentSINC\backend
    py -3 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    pip install -r requirements.txt

Check Ollama:

    ollama list

If Ollama is not running, launch the Ollama application first. The runtime automatically detects installed models and selects a local model. You can later select a different installed model in the AgentSINC Studio panel.

## Start the API

Open one PowerShell window:

    cd E:\AgentSINC\backend
    .\.venv\Scripts\Activate.ps1
    uvicorn app.main:app --host 127.0.0.1 --port 8000

## Start the 24/7 local worker

Open a second PowerShell window:

    cd E:\AgentSINC\backend
    .\.venv\Scripts\Activate.ps1
    python -m app.worker

Keep both processes and Ollama running. The API and worker bind to localhost; do not change the host to 0.0.0.0 or expose port 8000 publicly. The frontend polls the API every few seconds and displays the worker heartbeat and Ollama availability.

## One-click launcher

After creating the virtual environment and installing the requirements, run from the repository root:

    .\infra\start-local.ps1

It opens separate API and worker PowerShell windows. Keep both open while the local runtime is in use.

## Optional local environment configuration

The backend loads `backend/.env` on startup. To configure optional Google Search grounding for the Research Agent:

    Copy-Item .env.example .env
    notepad .env

Set `AGENTSINC_GOOGLE_SEARCH_ENABLED=true`, `GEMINI_API_KEY` and optionally `AGENTSINC_GOOGLE_SEARCH_MODEL=gemini-2.5-flash`. Keep `.env` private and never commit the key. Restart the API and worker after editing it. Google Search grounding is disabled unless the setting and key are both present. See [local learning memory and Google research](../docs/LOCAL_LEARNING_AND_GOOGLE_RESEARCH.md) for privacy and free-tier details.

## Local Ollama performance defaults

The default local tuning targets a laptop GPU with 4 GB VRAM and Ollama's 4K context:

- Workspace source snapshot: 9,000 characters by default (bounded configurable range: 6,000–14,000).
- Ollama context: 4,096 tokens by default (configurable range: 2,048–8,192).
- Specialist output: maximum 650 tokens.
- CEO plan: maximum 850 tokens.
- CEO synthesis: maximum 900 tokens.
- Qwen 3 thinking mode is disabled for routine specialist and orchestration calls.
- Model keep-alive: 20 minutes to reduce reloads between sequential stages.
- One worker remains the default; do not enable parallel inference on a 4 GB VRAM GPU without measuring memory and latency.

Optional environment overrides:

    $env:AGENTSINC_CONTEXT_MAX_CHARS = "9000"
    $env:AGENTSINC_OLLAMA_CONTEXT_TOKENS = "4096"
    $env:AGENTSINC_SPECIALIST_MAX_TOKENS = "650"
    $env:AGENTSINC_CEO_PLAN_MAX_TOKENS = "850"
    $env:AGENTSINC_CEO_SYNTHESIS_MAX_TOKENS = "900"
    $env:AGENTSINC_OLLAMA_KEEP_ALIVE = "20m"

The latest completed specialist response records prompt tokens, generated tokens, model load time, elapsed time and measured generation tokens/second in the runtime overview. The Studio settings panel displays these metrics. Compare several missions before deciding whether to change model, context or output budgets.

These are conservative starting values, not a guaranteed speed increase. Shorter context and output limits trade report length for latency; review the deliverables for quality before reducing further.

## Read-only project workspace

The worker automatically treats the repository root as its workspace (the directory containing `backend/` and `frontend/`). Override it only when needed:

    $env:AGENTSINC_WORKSPACE_ROOT = "E:\\AgentSINC"

Each mission receives a bounded, read-only snapshot of project documentation and relevant source files. The local API also provides:

- `GET /api/v1/workspace/summary`
- `GET /api/v1/workspace/files`
- `GET /api/v1/workspace/search?q=...`
- `GET /api/v1/workspace/read?path=...`

Absolute paths, parent-directory traversal and symbolic links are rejected. Dependency/build folders and sensitive files are excluded. Common credential patterns are redacted before file content is sent to Ollama. See [Workspace security](../docs/WORKSPACE_SECURITY.md).

This is bounded lexical retrieval, not a complete semantic index. It does not grant the model an unrestricted filesystem tool.

## What works in this phase

- Real, persistent six-agent roster: CEO, Team Lead, Developer, Designer, Researcher and QA.
- CEO founder requests routed to the Team Lead for planning, specialist delegation and report synthesis.
- Individual specialist report access directly from each Mission Board assignment.
- Specialist delegation limited to Developer, Designer, Researcher and Tester.
- Create a mission and assign it to an agent.
- Queue, run, complete and fail mission states.
- Per-agent and global event history.
- Pause/resume an agent (pause prevents new missions; an in-flight local model response finishes).
- Cancel queued work immediately or request cancellation while a response is streaming.
- Retry failed/cancelled missions.
- View the current result and task progress in the workspace.
- See API, worker heartbeat, Ollama connection, installed models and selected model.

## CEO and Team Lead orchestration

Select SINC CEO or Team Lead in the 3D office and submit a founder request. The CEO is the founder-facing entry point; the Team Lead owns planning, delegation and synthesis. The Team Lead then:

1. Reads the same bounded, read-only workspace snapshot and relevant local learning records.
2. Produces a JSON plan with one to four specialist missions.
3. Validates that every delegated agent is one of Developer, Designer, Researcher or Tester.
4. Persists the plan and specialist tasks in SQLite.
5. Executes specialist tasks sequentially through the local Ollama worker (one model request at a time).
6. Waits for all specialist tasks to reach a terminal state.
7. Synthesizes the actual specialist results into a CEO report.

The Mission Board shows Team Lead orchestration stage, specialist assignments, task progress, cancellation, each individual specialist report and the consolidated CEO report. Founder requests, plans, child missions and events survive restarts. If the worker restarts during planning or synthesis, the stage is retried; interrupted specialist missions are safely requeued unless cancellation was requested.

This is sequential coordination, not parallel model execution. It does not create independent always-running model processes for each character. All specialist work shares the selected local Ollama model and the one local worker.

## Agent Harness, real tools and approval boundaries

The local worker uses a role-scoped Agent Harness by default (`AGENTSINC_AGENT_HARNESS_ENABLED=true`). Each specialist receives a bounded tool list, can make up to eight tool calls per mission, and must report actual tool results rather than infer that an action succeeded.

| Agent | Built-in tools |
|---|---|
| Developer | Search/read repository files; propose a source write; run a fixed test suite |
| Designer | Search/read repository files; propose frontend/source edits; run a fixed test suite |
| Researcher | Search/read repository files; optional Google Search-grounded research |
| QA / Tester | Search/read repository files; run a fixed test suite |

**Real code changes:** `workspace.write_file` creates an approval request. The API does not modify the workspace until the founder approves that exact stored payload. Approved writes are atomic and limited to existing directories under `backend/app`, `backend/tests`, `frontend/src` and `docs`. Dependency manifests, lockfiles, environment files, secrets, arbitrary file types, path traversal and symlink destinations are refused. An approved local file write is not automatically a Git commit or push.

**Real tests:** `tests.run` accepts only `python-tests`, `python-syntax`, `frontend-typecheck` and `frontend-build`. It requires Docker and the configured `AGENTSINC_SANDBOX_IMAGE`. The sandbox has no network, a read-only source mount, a disposable tmpfs execution copy, dropped Linux capabilities and CPU/memory/process limits. If Docker or the image is unavailable, the tool returns `not_run`; it never falls back to executing repository code on the host.

Build the optional local test image from the repository root:

    docker build -t agentsinc-sandbox:local -f backend/Dockerfile.sandbox .
    
Then set `AGENTSINC_SANDBOX_IMAGE=agentsinc-sandbox:local` in `backend/.env` and restart the worker.

**Google research:** only the Research Agent receives `research.google_search`. It is disabled unless `AGENTSINC_GOOGLE_SEARCH_ENABLED=true` and `GEMINI_API_KEY` are both present. The external request contains the Research Agent's mission/question, not the local workspace snapshot or local memory. Google free-tier terms and availability are controlled by Google.

**MCP integrations:** the registry discovers tools only from servers explicitly listed in `AGENTSINC_MCP_SERVERS_JSON`. It does not install or connect to arbitrary plugins or unknown servers. Each server must specify its transport, agent roles, `allow_tools` and `read_only_tools`. Only explicitly read-only tools execute immediately; every mutating MCP tool creates a founder approval request. Store credentials as named environment-variable references, never inline in the JSON.

GitHub repository creation, remote file writes, pull requests or pushes are possible only when a GitHub MCP server is configured with the exact required tools and scopes. Those remote mutations remain approval-gated. Without that configuration, the local Developer can edit approved workspace files but cannot claim to have pushed them to GitHub.

The six office characters share one local Ollama model and one sequential worker; they are not six independent model processes. Completed missions are stored as bounded records in local SQLite memory (maximum 500); up to three relevant records may be retrieved as historical context. This is retrieval memory, not fine-tuning or model-weight training.

The runtime remains a local-first development system: SQLite, localhost API, local Ollama and one worker. Public multi-user authentication, production database/queue deployment, backup/restore, continuous monitoring, security review and a sustained 24-hour reliability test remain production release gates.

## Zero-cost and 24/7 expectations

Ollama local inference and this runtime do not charge per model call. Your computer supplies the CPU/GPU, RAM, storage, electricity and network connection. For continuous operation, Windows must stay awake, Ollama/API/worker must remain running, and the computer must remain powered and connected. If the PC sleeps, shuts down, loses power or loses connectivity, the worker pauses. This is a 24/7-capable local setup, not a guaranteed cloud SLA.

A free cloud web tier is not a dependable substitute for the always-on worker. Public remote access, multi-user authentication, backup/restore, sandboxing and production monitoring are later phases.


## GitHub development pipeline

AgentSINC can use the official GitHub MCP server when it is configured explicitly in `backend/.env`. The Team Lead sequences implementation, QA and publishing as separate specialist tasks. The Developer can create a feature branch and propose a GitHub file push only after the QA Agent has recorded a passing Docker test run. A pull request can be opened only after a successful feature-branch push. Each remote mutation pauses for founder approval, and agent merge operations are blocked.

See [GitHub development workflow](../docs/GITHUB_DEVELOPMENT_WORKFLOW.md) for Docker setup, the role-specific allowlist, required repository permissions and local verification steps. The Settings panel also exposes live MCP connection and tool-discovery status.
