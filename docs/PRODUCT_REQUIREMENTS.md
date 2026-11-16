# AgentSINC product requirements

## Product statement

AgentSINC is SINC's own AI company office: a custom 3D workspace where a CEO/orchestrator agent coordinates specialist AI agents and human teammates. The visual office makes work visible; the task system, API and database remain the source of truth.

## Primary outcomes

1. Elango and authorized SINC leaders can create, assign and monitor work.
2. A CEO agent can break a user goal into smaller tasks and delegate to specialist agents.
3. Developer, Designer, Researcher and Tester agents can collaborate through explicit task handoffs.
4. Human team members can inspect work, provide feedback and approve sensitive actions.
5. The company runtime and queued jobs keep operating when no browser is open.

## Product roles

### Human roles
- Founder / Owner: full company administration, runtime configuration and approval authority.
- Co-founder / Admin: delegated company administration, task oversight and approved operations.
- Advisor: read/review access as granted.
- Team member: assigned tasks, conversations, reviews and relevant office areas.

### AI roles
- CEO / Orchestrator: understands goals, plans tasks, delegates and synthesizes results.
- Developer: implementation, code review and technical debugging within approved workspaces.
- Designer: UX flows, visual systems and design assets.
- Researcher: research plans, source-backed findings and summaries.
- Tester / QA: test plans, verification, bug reports and regression checks.

AI roles are capabilities and policies, not just labels on avatars. Every agent must have a scoped instruction set and permission profile.

## MVP surfaces

- 3D Office: agent characters, departments, work zones and visible activity states.
- Dashboard: task pulse, running jobs, pending approvals, recent events and service status.
- Agents: profiles, responsibilities, current work, model/provider and conversation history.
- Task Board: backlog, assigned, in progress, review, blocked and completed states.
- Inbox / Activity: handoffs, agent messages, human comments and notifications.
- Approvals: pending privileged actions with request context, diff/evidence and approve/reject.
- Settings: team, providers, budgets, security and deployment status.

## Required runtime behavior

- Tasks and conversations are durable and survive deploys/restarts.
- Browser closure must not stop queued or running jobs.
- Long-running work must expose progress, last heartbeat, cancellation and terminal state.
- Agent-to-agent collaboration is recorded as task assignments and messages.
- A human can pause an agent, cancel a task and revoke an integration.
- The system must explain when it lacks evidence or permission instead of fabricating completion.

## Explicit non-goals for early phases

- No autonomous public deployment or production database mutation.
- No unrestricted shell, filesystem, browser or network access.
- No self-approval by agents.
- No promise of zero downtime from a single instance.
- No local LLM dependency for cloud uptime; the production provider must be reachable from the hosted runtime.
- No copying Hermes3D product code or office assets.

## Initial service quality targets

These are design targets for later validation, not claims of current performance:
- API health endpoint and worker heartbeat.
- Idempotent task creation/dispatch.
- Bounded retries and explicit failed/dead-letter states.
- Structured audit events for every state transition and tool invocation.
- Graceful worker shutdown and safe retry after restart.
- Accessible non-3D paths for core chat/task/approval workflows.
