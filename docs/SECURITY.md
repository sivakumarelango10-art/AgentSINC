# AgentSINC security baseline

This document defines minimum controls. It does not claim that these controls are implemented yet.

## Trust boundaries

- Browser: untrusted client; all submitted IDs, role labels and payloads require server validation.
- API: authenticated policy enforcement and system-of-record writes.
- Agent/model: probabilistic and potentially prompt-injected; never trusted as an authority.
- Tool broker: enforces explicit permissions, schemas, timeouts and audit records.
- Worker: long-running service with least-privilege credentials.
- Sandbox: isolated boundary for any future execution of untrusted code.
- External providers and integrations: secrets remain server-side; responses are untrusted data.

## Required controls before autonomous tools

1. Deny by default. Each agent receives only named capabilities and scoped resources.
2. Separate planning from execution. A model proposing an action does not authorize it.
3. Require human approval for destructive actions, deployments, external communications, credential changes and production mutations.
4. Record requester, agent, tool, validated arguments, policy decision, approver, timestamps, result and correlation ID.
5. Apply per-call and per-run timeouts, cancellation, output limits, concurrency limits and cost budgets.
6. Make retryable operations idempotent. Do not blindly repeat a payment, deployment or message send.
7. Do not expose production secrets to model prompts, user-visible logs or untrusted code.
8. Isolate code execution from the API/worker host. No host Docker socket or unrestricted host mounts.
9. Default sandbox network egress to denied; add narrow destinations only after review.
10. Validate URLs and destinations to prevent SSRF, private-network access and metadata-service access.
11. Treat source files, webpages, repository content and tool output as data, never as policy instructions.
12. Provide pause, revoke, cancel and emergency-stop controls.

## Identity and access

- Use secure, httpOnly, sameSite cookies for browser sessions.
- Enforce CSRF protection on cookie-authenticated mutations.
- Hash passwords with a modern password-hashing algorithm; support MFA before broad team access.
- Apply role-based access at the API layer, not only in the UI.
- Rotate and scope integration tokens. Never store plaintext secrets in PostgreSQL unless encrypted with a managed key.
- Rate-limit login, token issuance, task creation and expensive model operations.

## Data handling

- Store team profile fields needed by the product only.
- Keep private contact details and uploaded personal portraits out of public Git history.
- Encrypt traffic with HTTPS and use TLS for external database/queue connections.
- Back up PostgreSQL and regularly test restoration.
- Define retention and deletion policies before uploading customer or employee documents.

## Operational controls

- Keep dev, staging and production credentials separate.
- Require CI checks and reviewed pull requests before production deploys.
- Use dependency/security scanning and secret scanning.
- Log security-relevant events without logging credential values or full sensitive prompts.
- Test worker crash recovery, lease expiry, retries and emergency stop.

## Not enabled in Phase 1

No shell, arbitrary filesystem, browser automation, arbitrary network fetch, deployment, secrets management or autonomous production mutation is being enabled in this foundation phase.
