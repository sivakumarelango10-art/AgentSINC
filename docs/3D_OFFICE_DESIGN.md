# AgentSINC original 3D office design

## Design intent

The 3D headquarters is the primary product experience, not a small widget inside an admin dashboard. The office should feel like an explorable, living digital workplace while keeping real tasks, status and approvals in accessible overlay panels.

This is a new AgentSINC scene and design system. Do not copy or import Hermes3D code, assets, rooms or UI.

## Spatial layout

The first floor is a custom open-plan technology studio:

1. **SINC Command Hub** — central octagonal operations table and CEO agent.
2. **Development Studio** — workstation, glass divider and build display.
3. **Design Studio** — visual review/moodboard wall and designer workstation.
4. **Research Library** — research desk and book/archive shelving.
5. **Quality Lab** — test bench and QA workstation.
6. **Collaboration Lounge** — glass meeting room with shared table.
7. **Reception / Identity Wall** — branded entry feature and SINC visual identity.
8. **Perimeter planting and lighting** — adds depth, scale and a softer office atmosphere.

Rooms are 3D navigation metaphors. Tasks, agent identities and activity remain server-owned data once the API is integrated.

## Interaction model

- Full-window 3D scene occupies the background and remains the primary visual focus.
- Floating top bar shows brand, office/floor context and runtime mode.
- Compact icon rail opens Agents, Missions, Activity, People, Approvals and Studio panels.
- Room dock focuses the camera on Command, Development, Design, Research or Quality zones.
- Agent selection in the 3D scene synchronizes with the agent inspector and specialist roster.
- 2D floor-map mode gives a lighter alternative and must provide a working return-to-3D action.
- Orbit, pan and zoom are constrained to avoid losing the floor.

## Visual language

The current design is a cinematic dark digital office:
- Layered glass surfaces and subtle borders for overlays.
- Warm, controlled light, deep blue structural materials and room-specific accent strips.
- Floating room and agent labels that remain legible over the scene.
- Brand theme can switch between cyan/violet, ember and indigo/lime.
- Avoid a dense traditional admin sidebar, multi-card dashboard grid, large blank margins or a tiny 3D viewport.

## Character system

AI agents use original stylized low-poly characters with role-specific colors. Visual states:
- Idle
- Working
- Thinking
- Collaborating
- Waiting for approval

Agent animations are driven by state data. Never animate a completed status when the backend has not confirmed completion.

## Asset and performance rules

- Keep the logo assets inside `frontend/public/brand/` so Next.js can serve them.
- Use original Three.js geometry or properly licensed custom models.
- Lazy-load the WebGL scene.
- Use adaptive pixel ratio and quality presets.
- Keep the 2D floor map and accessible panels usable without WebGL.
- Respect reduced-motion preferences.
- Profile the final scene on desktop and mobile before production deployment.

## Current prototype status

Implemented in the Phase 2 branch:
- Full-window 3D viewport and original office environment.
- Command hub, glass meeting room, specialist departments, desks, shelves, test bench, moodboard, plants and branded reception wall.
- Stylized selectable agent characters.
- Room-focused orbit targets.
- Floating workspace UI, panel rail, agent/mission/activity/team/approval/settings panels and 2D floor map.

Not yet implemented:
- Persistent camera presets and movement animations between rooms.
- Human team avatars in the scene.
- Live API-driven agent state, tasks and activity.
- Production authentication, 24/7 backend/worker, database and monitoring.
