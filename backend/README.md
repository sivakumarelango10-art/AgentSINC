# AgentSINC API

This directory will contain the FastAPI service.

Planned responsibilities:
- Authentication and authorization.
- Team, employee, agent, task, conversation and approval APIs.
- PostgreSQL models and Alembic migrations.
- Provider adapter and orchestration contracts.
- Durable event publication and health/readiness endpoints.

The API is the system-of-record boundary. It does not run long model tasks inside request handlers; it records and enqueues work for the worker.
