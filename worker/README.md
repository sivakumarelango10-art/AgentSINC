# AgentSINC worker

This directory will contain the always-on background worker entrypoint.

Planned responsibilities:
- Claim and execute queued agent runs.
- Send heartbeats and renew job leases.
- Persist progress, messages, outputs and terminal state.
- Support retry, cancellation, graceful shutdown and dead-letter handling.
- Invoke only tools approved by the server-side policy and scope.

The worker must run independently of the web browser. It must not execute untrusted code directly in its own process.
