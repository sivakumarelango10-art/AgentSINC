# AgentSINC web application

The Phase 2 prototype uses Next.js App Router, React 19, TypeScript, Tailwind CSS 4 and React Three Fiber v9.

## Requirements

- Node.js 20.9 or newer (Node 22 LTS recommended).
- npm 10 or newer.

## Run locally

From this directory:

```powershell
npm install
npm run dev
```

Open `http://localhost:3000`.

For production build validation:

```powershell
npm run typecheck
npm run build
```

## Phase 2 prototype

This is a visual prototype with sample data. It includes:
- Theme switching across all three supplied logo palettes.
- A custom procedural 3D office scene built from original geometry.
- Selectable CEO, Developer, Designer, Researcher and Tester agents.
- A simple 2D floor-map fallback for devices without reliable WebGL support.
- Responsive dashboard cards for active tasks and activity.

It is not connected to authentication, the database, the API, model providers or a background worker yet. The 2D/3D views share the same sample data, and clicking an agent updates the inspector.

## Important

The API and worker will be implemented in their own services in later phases. Do not add provider secrets to frontend environment variables. Run `npm install` to create the local lockfile before making further dependency changes.
