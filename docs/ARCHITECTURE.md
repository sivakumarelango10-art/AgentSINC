# AgentSINC system architecture

## Architecture decision

Use a small monorepo with separately deployable web, API and worker processes. Keep the 3D office as a custom frontend experience. Keep orchestration and durable business state on the server.

## Proposed stack

| Layer | Technology | Responsibility |
|---|---|---|
| Web | Next.js, React, TypeScript, Tailwind CSS | Dashboard, settings, chat, task board |
| 3D | Three.js, React Three Fiber, Drei | Original office scene, avatars, camera and interactions |
| Client state | Zustand for local UI state; TanStack Query for API cache | UI only; never the canonical record |
| API | Python, FastAPI, Pydantic | Auth, validation, permissions, business rules and events |
| ORM / migrations | SQLAlchemy 2.x, Alembic | Typed data access and schema evolution |
| Database | PostgreSQL | Durable company state |
| Queue | Redis + Celery | Background execution, retries and worker coordination |
| AI integration | Provider adapter interface | Local development provider and production hosted provider |
| Observability | Structured logs, metrics and error reporting | Health, latency, queue age, cost and failure visibility |

Versions will be pinned in the implementation phase after compatibility and security checks.

## Monorepo layout

```text
AgentSINC/
  frontend/       Next.js app and original 3D office
  backend/        FastAPI application, schemas, models and migrations
  worker/         Long-running task worker entrypoint and job handlers
  infra/          Docker Compose, deployment manifests and operations config
  public/brand/   Approved AgentSINC brand assets
  team/           Public team-role metadata, no private contact data
  docs/           Product, architecture, security and operations decisions
  tests/          Cross-service and end-to-end tests
```

## Runtime topology

```text
Browser
  | HTTPS / SSE or WebSocket
  v
Next.js Web App
  | authenticated API calls
  v
FastAPI API  <------> PostgreSQL (system of record)
  |
  +---- enqueue job ----> Redis
                            |
                            v
                       Agent Worker
                            |
                            +----> Model Provider Adapter
                            |
                            +----> Scoped Tool Broker
                                      |
                                      +----> Approval Service
                                      +----> Isolated Sandbox (later phase)
  |
  +---- publish activity / status events
```

The browser is a visualization and interaction client. Closing it must not terminate work. The worker is the long-running process that pulls queued jobs, executes bounded orchestration steps, writes state and publishes events.

## Canonical records

Initial entity groups:
- Identity: users, sessions, roles, team memberships.
- Company: departments, people, agent profiles, room assignments.
- Work: tasks, assignments, dependencies, task events and artifacts.
- AI: agent runs, sessions, conversations, messages, provider configuration references and usage.
- Governance: approvals, tool grants, audit events and policy versions.
- Operations: worker heartbeats, job attempts, provider health and system events.

PostgreSQL owns durable state. Redis is a coordination/queue layer, not the only copy of a task or conversation.

## Orchestration lifecycle

1. API authenticates the user and validates the request.
2. API creates a task and an auditable run record in PostgreSQL.
3. API enqueues the run; it does not execute the agent inline.
4. Worker claims the job with a lease/heartbeat and loads current policy.
5. CEO agent plans bounded subtasks and delegates only to enabled specialists.
6. Specialist results, evidence and messages are persisted.
7. Privileged actions become approval requests; the worker waits or safely exits the attempt.
8. Worker writes a terminal state and publishes events.
9. UI reflects persisted state and events; it never invents a successful result.

## 3D office approach

The scene will be authored specifically for AgentSINC:
- Distinctive SINC headquarters layout with a CEO/operations hub and specialist zones.
- Custom procedural or original low-poly furniture, materials, lighting and props.
- Agent characters driven by a small state machine: idle, walking, working, collaborating, waiting for approval and offline.
- Click/tap selection opens a normal accessible agent/task panel.
- Scene rendering is lazy-loaded; provide quality controls, LOD, instancing and a 2D fallback.

The team images supplied during planning can be used later only after the final page and image handling are approved. Do not put portrait images into public repository assets by default.

## API principles

- Version external endpoints under `/api/v1`.
- Use typed request/response schemas and consistent error envelopes.
- Enforce permissions in the API for every mutation.
- Use idempotency keys for task dispatch and external side effects.
- Publish durable domain events via an outbox pattern before adding real-time fan-out.
- Keep secrets server-side and never return raw provider credentials to the browser.

## Important constraints

The production runtime must use non-sleeping compute. Free tiers can be used for previews or non-critical static assets, not for the worker expected to remain available. See [DEPLOYMENT.md](DEPLOYMENT.md).
