# AgentSINC

**An original 3D AI company office for the SINC team.**

AgentSINC is being built from scratch as SINC's own product. It is not a Hermes3D fork or rebrand. The goal is a persistent, secure, observable AI company runtime with an original 3D office where a CEO/orchestrator agent coordinates specialist agents, team tasks, collaboration and approvals.

## Product vision

- A custom 3D office and original AgentSINC visual identity.
- A CEO / orchestrator agent that can plan work and delegate to specialist agents.
- Developer, Designer, Researcher and Tester agents with clear responsibilities.
- Human-readable task boards, conversations, approvals, execution history and audit trails.
- A reliable always-on API and worker process, with durable database-backed state.
- Human approval before privileged or irreversible actions.

## Founding team

| Person | Role |
|---|---|
| Elango S | Founder |
| Karmjit SG | Co-founder |
| Prajith P | Co-founder |
| Aaditya R M | Founding Advisor |
| Vaishnavi M | Tester |
| Meghana P Banda | Tester |
| Dhakshatha S | Developer & Social Media Team |
| Ishita Das | Designer |
| Mohana Priya G | Designer |
| Dhanusri T | Tester & Developer |
| Gopika S | Developer |

## Proposed technology baseline

The exact implementation will be locked in Phase 1 after the repository and deployment constraints are reviewed.

- **Web app:** Next.js, React, TypeScript, Tailwind CSS.
- **3D office:** Three.js / React Three Fiber with original scene assets and interaction logic.
- **API and orchestration:** Python, FastAPI, typed service boundaries.
- **Data:** PostgreSQL with migrations; Redis-backed job queue when background execution is introduced.
- **AI providers:** provider adapter interface, so development can use a local model and production can use a configured hosted provider without coupling the product to one model vendor.
- **Hosting:** separate web, API, worker and database responsibilities; paid always-on compute for production services that must not sleep.

## Delivery principles

1. Build in small phases with clear acceptance tests.
2. Keep every phase reviewable through GitHub branches and pull requests.
3. Do not copy Hermes3D source, assets or UI. Create AgentSINC's own design and runtime.
4. Keep task records, conversations, agent state and audit events durable in PostgreSQL.
5. Treat agent execution as untrusted work: least privilege, scoped tools, timeouts, cancellation, approvals and audit logs.
6. Never commit API keys, tokens, passwords, database URLs or private user data.

## Roadmap

See [docs/PHASES.md](docs/PHASES.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/SECURITY.md](docs/SECURITY.md) and [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

**Current status:** Repository bootstrap. Phase 1 foundation is being prepared.
