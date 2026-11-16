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

The selected direction is a **white-first, realistic modern technology headquarters**:
- White and warm-white are the primary surfaces for the interface, architecture and furniture.
- Use natural materials such as oak/walnut veneer, pale stone, brushed aluminum, ceramic, clear/frosted glass, fabric upholstery and realistic foliage.
- Bring color through room identity, textiles, artwork, screens, agent clothing and accent lighting rather than turning the entire environment into a dark neon scene.
- Department palette: orchid/violet for Command, sky/cobalt for Development, coral/rose for Design, amber for Research and emerald for Quality.
- The studio theme control can switch complementary accent combinations while keeping the white architectural base consistent.
- Use daylight, soft shadow contact, restrained reflections and realistic roughness/metalness values.
- Keep overlays bright, translucent and legible with dark charcoal typography.
- Avoid a dense traditional admin sidebar, multi-card dashboard grid, large blank margins or a tiny 3D viewport.

The first pass uses original procedural geometry and physically based materials to establish realistic proportions and surfaces. Photorealistic asset models and fine-detail prop dressing can be added later without replacing the original layout or interactions.

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
- Selectable agent characters with natural skin/hair tones and department-colored clothing.
- Room-focused orbit targets.
- Floating workspace UI, panel rail, agent/mission/activity/team/approval/settings panels and 2D floor map.

Not yet implemented:
- Persistent camera presets and movement animations between rooms.
- Human team avatars in the scene.
- Live API-driven agent state, tasks and activity.
- Production authentication, 24/7 backend/worker, database and monitoring.


## White-first realism update

The current Phase 2 implementation has been updated to use a bright architectural base: warm-white porcelain floor, frosted glass partitions, brushed metal framing, oak worktops, pale command furniture, ergonomic upholstered chairs, ceramic planters, daylight-balanced lighting and a multicolor department system. The three accent theme options now change accent combinations while the core interface and office remain white-first.
