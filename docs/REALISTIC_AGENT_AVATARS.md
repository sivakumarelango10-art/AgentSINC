# AgentSINC realistic agent avatars

AgentSINC can display locally hosted, rigged human characters instead of its procedural fallback figures.

## Generate the six character assets

Requirements: Node.js 20+ and PowerShell on Windows.

From the AgentSINC repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\generate-agent-avatars.ps1
```

The first run uses the Ara 3D Gen CLI to build six high-detail characters and downloads its character data. The generator uses MakeHuman character assets; its source code is MIT-licensed and its bundled MakeHuman assets are CC0. The character files are generated on your computer. No avatar API key, subscription or paid generation service is used.

The command creates:

- `frontend/public/models/agents/ceo.glb`
- `frontend/public/models/agents/team_lead.glb`
- `frontend/public/models/agents/developer.glb`
- `frontend/public/models/agents/designer.glb`
- `frontend/public/models/agents/researcher.glb`
- `frontend/public/models/agents/tester.glb`
- `frontend/public/models/agents/manifest.json`

Each GLB includes the selected idle, walk, run, talk and chair-sitting animation clips. The 3D scene loads these files from the same AgentSINC origin and drives clips from persisted agent location and status. It does not call a remote avatar runtime.

## Development and deployment

Restart the frontend after generation and reload `http://localhost:3000`. If the manifest is disabled or a model is missing, AgentSINC keeps its existing procedural avatar fallback.

The generated files are local outputs and are intentionally not committed by the generator. To include the realistic characters in a Git/Vercel deployment, review the six generated GLBs and then add them to the repository:

```powershell
git add frontend/public/models/agents/*.glb frontend/public/models/agents/manifest.json
git status --short
```

Review the resulting repository size before committing. Keep the `manifest.json` enabled only when all six matching GLBs are present.

## References and licences

- Ara 3D Gen source: https://github.com/olatunde85/3d-gen
- Ara 3D Gen self-hosting and CLI: https://ara3dgen.com/docs/self-hosting/
- MakeHuman asset licence: https://www.makehumancommunity.org/about/license.html

Ara 3D Gen code is MIT-licensed. The MakeHuman core assets used by its character generator are CC0. Review the upstream licences if you replace the source generator or add third-party garments, props or textures.
