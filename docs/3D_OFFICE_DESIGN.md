# Original AgentSINC 3D office concept

## Design intent

Create a distinctive virtual SINC headquarters that makes agent activity understandable at a glance. This is a new scene and design system, not a copy of Hermes3D or another virtual office.

The uploaded SINC team screenshots are visual references for the people and roles, not an instruction to place personal portraits directly on AI agent characters. Human team members and AI agent avatars should be separate concepts in the product.

## Spatial layout

The first prototype should use one compact, readable floor:

1. **Reception / Lobby** — SINC identity, system pulse and entry point.
2. **CEO / Command Hub** — central orchestration desk with active tasks and team overview.
3. **Development Studio** — developer agents, code/review desks and build status.
4. **Design Studio** — design agents, moodboards and review workspace.
5. **Research Library** — research agents, source collections and evidence status.
6. **QA Lab** — tester agents, test runs, defects and release gates.
7. **Collaboration Room** — agents and human teammates can meet around a shared task.
8. **Quiet / Idle Zone** — agents without active work remain visibly idle rather than pretending to be busy.

Rooms are navigational metaphors. Task and agent records remain in the API/database, not in the 3D scene graph.

## Character system

AI agents use original stylized avatars with consistent proportions and role-specific accents. Human users have profile cards and may later opt into portrait uploads.

Agent visual states:
- Idle — at desk or in the quiet zone.
- Walking — moving to a destination.
- Working — seated/standing at a workstation with subtle activity animation.
- Collaborating — present in the collaboration room.
- Waiting for approval — clearly marked, no false claim of progress.
- Offline / unavailable — dimmed or shown in the roster rather than animated as active.

Animations are driven by persisted server state and transient presentation events. The scene must never generate a fake task completion state.

## Navigation and interaction

- Orbit, pan and zoom camera on desktop.
- Click or tap an agent to open an accessible detail panel.
- Click a room to focus the camera and show that department's queue.
- Provide keyboard navigation and a 2D list/room map alternative.
- Keep chat, task assignment and approvals in normal semantic UI panels.
- Make the 3D scene lazy-loaded so the dashboard shell remains fast.

## Visual direction

The logo source currently offers three themes:
- Cyan + Violet
- Ember
- Indigo + Lime

Do not hard-code the whole UI to one palette before the team chooses. Use semantic design tokens for background, surface, text, accent, status and department colors.

The office should use a controlled material system, readable labels and lighting that does not hide important state indicators. Avoid excessive bloom, post-processing or tiny text floating in 3D.

## Performance targets for Phase 2

These are prototype targets to measure:
- Desktop: aim for smooth 60 FPS on a mid-range integrated/discrete GPU.
- Mobile: aim for a stable 30 FPS mode with reduced shadows and effects.
- Load the office only when the user opens it.
- Use instancing and level-of-detail for repeated furniture/props.
- Keep critical workflows available in 2D if WebGL is unavailable or reduced motion is preferred.

## Phase 2 acceptance

- Original scene built with Three.js / React Three Fiber.
- No copied Hermes3D scene, models, code or product UI.
- Room navigation and agent selection work with sample data.
- Agent visual states are driven by typed data/state mapping.
- Responsive fallback, keyboard path and reduced-motion path exist.
- Performance is profiled and documented on at least one desktop and one mobile-class device.
