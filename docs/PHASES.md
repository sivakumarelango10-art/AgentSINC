# AgentSINC delivery phases

The project is developed one phase at a time. Each phase has a branch, pull request, acceptance criteria and a production-readiness decision. A later phase must not be described as finished merely because its UI exists.

## Phase 1 — Product and architecture foundation (current)

**Goal:** agree on what AgentSINC is, who uses it, how the services fit together, and what must be true for a safe 24/7 runtime.

Deliverables:
- Product requirements, service architecture and repository conventions.
- Founding-team roster, including Gopika S as Developer.
- Three supplied brand directions recorded without silently choosing one.
- Security boundaries and always-on deployment plan.
- Empty application boundaries for frontend, API, worker and infrastructure.

Acceptance:
- Product scope and non-goals are documented.
- No Hermes3D dependency or copied office scene exists.
- Persistent data, API, worker and browser responsibilities are explicit.
- Production plan excludes sleep-prone free compute for the agent runtime.
- The Phase 1 pull request is reviewed and merged before implementation begins.

## Phase 2 — Original UI system and 3D office prototype (in progress)

**Goal:** build the AgentSINC look and feel, dashboard shell and original interactive office.

Current branch progress: dashboard shell, brand theme switcher, selectable specialist-agent sample data, 2D floor-map fallback and a procedural React Three Fiber scene are now present. API/auth/database integration and production-ready assets remain later work within this phase.

Deliverables:
- Responsive dashboard, navigation, agent roster and task surfaces.
- Original 3D office blockout: lobby, CEO area, developer/design/research/QA zones.
- Original low-poly/stylized agent characters, desks and state animations.
- Orbit/pan/zoom camera, selectable agents and agent detail panels.
- 2D fallback and performance-quality settings.

Acceptance:
- No copied Hermes3D source, scene, models or UI.
- Office loads on desktop and degrades gracefully on mobile / low-power devices.
- Scene state is driven by typed sample data, not hard-coded character animation.
- Keyboard access and reduced-motion behavior are checked.

## Phase 3 — Local runtime, task persistence and agent controls (in progress)

**Goal:** make AgentSINC executable locally without paid model APIs or paid hosting. The first slice uses FastAPI, SQLite and a separate Ollama worker. Authentication and multi-user identity remain to be added before public access.

Current deliverables on the Phase 3 branch:
- Durable five-agent roster, missions and event timeline in SQLite.
- Local API for assignment, cancellation, retry, pause/resume and installed-model selection.
- A separate Ollama worker with streaming progress, cancellation, heartbeat, single-worker lease and restart recovery.
- Frontend polling and live agent/task/activity panels.

Acceptance still outstanding: verify on Elango's Windows machine with the installed Ollama model, run a sustained soak test, add authentication and backups, and decide whether the later production data store remains PostgreSQL.

## Phase 3B — Identity, team and production data

**Goal:** replace mock data with secure accounts and canonical team/agent/task records.

Deliverables:
- PostgreSQL schema and migration history.
- Founder/admin and team-member authentication.
- User, employee, agent, department, room and role management.
- Audit events and permission checks.
- API contracts and integration tests.

Acceptance:
- Restarting the app does not lose team, task or conversation records.
- Users can only access data/actions allowed by their roles.
- Migration and backup/restore procedures are tested.

## Phase 4A — Repository-aware local agents (in progress)

**Goal:** allow local agents to ground their analysis in the actual AgentSINC codebase without granting unrestricted host access.

Implemented on the Phase 4A branch:
- Read-only workspace rooted at the repository directory, with an optional explicit root override.
- Path confinement, traversal and symlink rejection, dependency/build folder exclusions and sensitive-file filtering.
- Common credential/token redaction before snippets are shown to Ollama.
- Bounded project file inventory, lexical search, file reading and context assembly.
- Mission prompts receive real source/documentation excerpts and are instructed to cite relative file paths.
- Local API endpoints expose workspace summary, file inventory, search and safe read.
- Tests cover workspace confinement, excluded paths, evidence retrieval and redaction.

Acceptance:
- Run the architecture-roadmap mission on Elango's Windows machine and verify it cites files that exist in the local repository.
- Confirm .env, dependency folders, virtual environments, build output and local SQLite data are excluded.
- Confirm traversal and symlink attempts are rejected.
- Confirm the model never claims to modify files, run tests or deploy.
- Measure indexing/search latency on the actual E: workspace.

Remaining: human-reviewed file patch proposals and apply-after-approval workflow are separate follow-up work. No shell or write tool is granted in this phase.

## Phase 4B — CEO orchestration and specialist handoffs (in progress)

**Goal:** make the CEO agent plan work and delegate explicit sub-missions to specialists.

Implemented on the Phase 4B branch:
- Durable CEO orchestration records separate from individual specialist task records.
- CEO plans generated as JSON and validated before dispatch.
- Delegation allowlist restricted to Developer, Designer, Researcher and Tester; maximum four specialist tasks per founder request.
- Specialist missions are persisted atomically and executed sequentially by the one local Ollama worker.
- CEO waits for specialist terminal results and produces one consolidated founder-facing report.
- Orchestration detail, child missions, stage, progress, result and cancellation are visible on the Mission Board.
- Cancellation propagates to queued/running child tasks; worker restart recovery preserves cancellation and resumes incomplete work safely.
- API and UI route requests submitted to SINC CEO into orchestration, while direct specialist missions keep their existing workflow.

Still outstanding:
- Verify a complete CEO → specialists → CEO cycle on Elango's Windows computer using qwen3:4b.
- Exercise cancellation, agent pause, model timeout and worker restart cases against the local SQLite database.
- Measure prompt/context size and mission duration on the actual computer.
- Add conversation threads and richer agent-to-agent message records after the sequential handoff workflow is verified.

Deliverables:
- Provider adapter contract with development and production configuration.
- CEO orchestrator, specialist agent profiles and explicit handoff protocol.
- Conversation persistence, tool-call records, retries and cancellation.
- Live agent status events to the 3D office.
- Usage limits, timeouts and per-agent budgets.

Acceptance:
- A user request can be decomposed into tasks and assigned to the right specialist.
- Agent messages and handoffs persist across service restarts.
- Failed or cancelled runs reach a terminal state and are visible.
- No unrestricted host shell or file tools are enabled.

## Phase 5 — Task lifecycle, approvals and controlled tools

**Goal:** move from simulated collaboration to guarded execution.

Deliverables:
- Task board, dependencies, assignments, evidence and execution history.
- Human approval queue for privileged actions.
- Narrow, allowlisted tools with typed inputs and outputs.
- Isolated sandbox for code execution, with resource and network controls.
- Audit trail for every tool request, approval and result.

Acceptance:
- Agents cannot self-approve privileged actions.
- A cancelled task stops work and records why.
- Untrusted code cannot access production secrets or the host filesystem.
- Only approved artifacts can leave the sandbox.

## Phase 6 — Always-on operations and team collaboration

**Goal:** operate the API and worker continuously and support real collaboration.

Deliverables:
- Separate web, API, worker, database and queue services.
- Durable job queue, retry policy, dead-letter handling and graceful shutdown.
- Real-time presence, task/activity feed and multi-user collaboration.
- Structured logs, metrics, health checks, alerting and backups.
- Rate limits, model budget controls and service recovery runbooks.

Acceptance:
- Agents continue queued work when the browser is closed.
- Restarting a worker does not lose queued task state.
- A 24-hour soak test completes with no stuck jobs or silent failures.
- Alerts fire for worker failure, queue age, database issues and repeated provider errors.

## Phase 7 — Production hardening and launch

**Goal:** verify the platform under realistic conditions and launch it.

Deliverables:
- Security review, dependency scanning and automated CI.
- Load, soak, recovery and backup-restore tests.
- Domain, HTTPS, production secrets and environment separation.
- Cost dashboard, usage quotas, incident runbook and rollback procedure.
- Final release checklist and operations guide.

Acceptance:
- No critical/high unresolved security findings.
- Production smoke tests, backup restore and rollback are demonstrated.
- Agent behavior is observable and all privileged actions are approval-gated.
- The owner explicitly approves production launch.

## Working rule

Finish and verify one phase before starting the next. A working screen is not proof that the API, database, worker, security controls or 24/7 operations are complete.


## Phase 4B.1 — Reliable CEO planning output

A live Windows test found that the installed Qwen 3 model could return a JSON object without the required `summary` field. The orchestration validator therefore stopped before creating specialist missions.

The planner now:
- Uses Ollama JSON-schema structured output with required `summary` and `tasks` fields.
- Disables Qwen 3 thinking for deterministic orchestration JSON and synthesis output.
- Sets temperature to zero and bounds planning output tokens.
- Accepts a small set of equivalent plan/task aliases as a compatibility fallback.
- Derives a factual one-line summary from validated specialist task titles if the model omits only the summary field.
- Still rejects missing, empty, invalid or out-of-scope specialist task lists.

Regression coverage verifies schema usage, Qwen thinking configuration, missing-summary recovery, supported aliases, and rejection of invalid delegation. Existing sequential worker and human-controlled tool boundaries remain unchanged.


## Local inference performance tuning — initial profile

Hardware measured on the founder's laptop: Intel Core i7-11850H (8 cores / 16 logical processors), 31.67 GB RAM, NVIDIA RTX A2000 Laptop GPU with 4 GB VRAM. `ollama ps` reported Qwen 3 4B at 34% CPU / 66% GPU with a 4,096-token context. This confirms GPU acceleration is active but the model is split across CPU and GPU.

Initial conservative tuning:
- Keep the context at 4,096 tokens; do not increase it on this 4 GB VRAM GPU without a benchmark.
- Reduce the workspace snapshot from 22,000 to 9,000 characters by default.
- Cap specialist responses at 650 tokens, CEO plan at 850 and CEO synthesis at 900.
- Disable Qwen 3 thinking mode for ordinary worker and orchestration responses.
- Keep the model resident for 20 minutes between sequential stages.
- Continue one worker / one generation at a time.
- Capture Ollama prompt tokens, generated tokens, load seconds and generation tokens/second for the most recent completed specialist response; show them in Studio Settings.

Acceptance:
- Backend tests verify inference payload limits and generation telemetry.
- Frontend typecheck and production build pass.
- Run the same representative mission before and after on the founder's laptop and compare first-token latency, tokens/second, total elapsed time and report quality.
- Keep the previous profile available for rollback if concise outputs omit important evidence.
