# AgentSINC web application

AgentSINC is an original SINC AI office. The Phase 2 visual prototype uses Next.js App Router, React 19, TypeScript, Tailwind CSS 4 and React Three Fiber v9.

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

## Current Phase 2 experience

- Full-window, immersive original SINC 3D headquarters. The office is the main workspace, not a small dashboard widget.
- Command Hub, Development Studio, Design Studio, Research Library, Quality Lab, Collaboration Lounge and SINC identity wall.
- Original procedural office geometry, desks, glass partitions, lighting, plants, room signage and stylized selectable AI characters.
- Room navigation that changes the OrbitControls target.
- Floating UI panels for agents, missions/tasks, activity, people, approvals and studio settings.
- Three switchable brand palettes.
- 2D floor-map mode with return-to-3D control.

All displayed agent/task/activity details are sample data. Authentication, PostgreSQL, API, AI providers and the background worker are not connected yet.

## Local development notes

- Keep npm cache and temporary files outside the system drive when needed, for example with `npm config set cache E:\\npm-cache --global`.
- The 3D environment is lazy-loaded, with a non-WebGL floor map alternative.
- Do not add provider credentials to frontend code or browser environment variables.
