# AgentSINC hosting and 24/7 operations plan

## What “24/7” means

The web app, API, database and background worker must remain available without relying on a founder's laptop or an open browser tab. The worker should be alive around the clock but should consume model tokens only when it has queued work or a scheduled check to perform.

A single cloud instance cannot promise zero downtime. Production readiness also requires health checks, persistent state, graceful restarts, monitoring, backups and a recovery procedure.

## Hosting layout

| Component | Production deployment | Must remain awake? |
|---|---|---|
| Frontend | Vercel or an always-on web service | Available through hosted frontend platform |
| FastAPI API | Paid always-on web service | Yes |
| Agent worker | Paid background worker / VM process | Yes |
| PostgreSQL | Managed paid PostgreSQL | Yes |
| Redis | Managed Redis / Key Value with persistence and availability appropriate to queue use | Yes |
| 3D assets | CDN/object storage or static hosting | Available on demand |
| Logs / alerts | Managed monitoring | Yes |

The API and worker are separate processes and scale independently. The database is the source of truth. The queue is not the only store of task state.

## Render guidance

Render is a candidate because the team already has a Render workspace. For production, use paid compute for API and worker services. Render's Free web services spin down after 15 minutes without inbound HTTP traffic or WebSocket messages, can take about a minute to wake, have ephemeral local filesystems and are documented as unsuitable for production. Paid compute plans do not spin down.

References:
- https://render.com/docs/free
- https://render.com/docs/faq
- https://render.com/pricing

Do not try to keep a free service awake with artificial ping traffic. It does not turn a free tier into a reliable 24/7 system.

## Database guidance

Use a managed PostgreSQL service with backups and no automatic inactivity pause for production. Free database tiers are useful for development and prototypes only; for example, Supabase documents that Free projects with low activity may be paused after a week.

Reference:
- https://supabase.com/docs/guides/platform/free-project-pausing

## First deployment sequence

1. Local development with Docker Compose for PostgreSQL and Redis.
2. Deploy a staging frontend and API; verify authentication, migrations and health endpoints.
3. Deploy a separate worker; verify heartbeat and queue recovery after restart.
4. Move the database to managed PostgreSQL with backups and TLS.
5. Add model provider secrets only to server-side environment configuration.
6. Add object storage only when attachments or execution artifacts are implemented.
7. Run a 24-hour soak test and backup restore test.
8. Promote to production after approval.

## Operational acceptance checklist

- API has liveness and readiness checks.
- Worker publishes a heartbeat and exits cleanly on SIGTERM.
- Jobs use leases, bounded retries and a dead-letter state.
- Browser closure does not stop a job.
- Database backups are enabled and restore-tested.
- Alert on API failure, stale worker heartbeat, old queue items, DB saturation and repeated provider errors.
- No credentials are stored in GitHub or browser storage.
- Deploys can roll back to a known-good version.

## Cost control

Always-on compute and managed data stores are paid services. Final monthly cost depends on the chosen instance sizes, database/Redis plans, region, bandwidth, model provider and job volume. We will select a small staging setup first, measure memory/CPU and queue behavior, then lock the production budget before launch.
