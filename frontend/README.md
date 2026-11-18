# AgentSINC web application

AgentSINC is an original SINC AI office. The frontend uses Next.js App Router, React 19, TypeScript, Tailwind CSS 4 and React Three Fiber v9.

## Requirements

- Node.js 20.9 or newer (Node 22 LTS recommended).
- npm 10 or newer.

## Run locally

From this directory:

    npm install
    npm run dev

Open http://localhost:3000.

For frontend validation:

    npm run typecheck
    npm run build

## Runtime connection

The browser connects to the local AgentSINC API at http://127.0.0.1:8000 by default. Start the FastAPI service and the separate Python worker, then keep Ollama running to enable real local missions.

Runtime setup, Windows commands, and zero-cost/24-hour limitations are documented in ../backend/README.md.

## Current experience

- Full-window, white-first SINC headquarters with original procedural architecture and multi-color department identities.
- Selectable human-proportioned 3D specialist agents with agent detail and timeline panel.
- Room navigation, 2D floor map, and workspace navigation.
- Persistent mission creation, queue, progress, result, cancellation and retry through the local API.
- Agent pause/resume controls and per-agent history.
- Runtime health display for API, worker heartbeat, local Ollama connection and installed model selection.

When the backend is not running, the UI explicitly shows runtime disconnected and does not display fake active work. The API and worker are local-only in this phase. File-system edits, browser automation, external integrations and deployment actions remain disabled until sandboxing and approval controls are implemented.
