"use client";

import dynamic from "next/dynamic";
import { useMemo, useState, type CSSProperties } from "react";
import {
  BRAND_THEMES,
  INITIAL_AGENTS,
  STATUS_LABELS,
  type BrandTheme,
  type OfficeAgent,
} from "./types";

const OfficeViewport = dynamic(() => import("./OfficeViewport"), {
  ssr: false,
  loading: () => (
    <div className="world-loading">
      <div className="loading-mark"><span /><span /><span /></div>
      <strong>Constructing SINC headquarters</strong>
      <small>Loading the office environment</small>
    </div>
  ),
});

type PanelKey = "agents" | "tasks" | "activity" | "team" | "approvals" | "settings";
type RoomKey = "all" | "command" | "development" | "design" | "research" | "quality";

const tasks = [
  {
    id: "AS-001",
    title: "Finalize AgentSINC product architecture",
    owner: "SINC CEO",
    status: "In progress",
    progress: 72,
    color: "violet",
    room: "Command Hub",
  },
  {
    id: "AS-002",
    title: "Build the original 3D office environment",
    owner: "Dev Agent",
    status: "In progress",
    progress: 64,
    color: "cyan",
    room: "Development Studio",
  },
  {
    id: "AS-003",
    title: "Explore the SINC visual identity",
    owner: "Design Agent",
    status: "Review",
    progress: 48,
    color: "rose",
    room: "Design Studio",
  },
];

const activity = [
  { time: "NOW", title: "CEO agent refreshed the company roadmap", detail: "Command Hub", color: "violet" },
  { time: "04 MIN", title: "Developer agent started the office build", detail: "Development Studio", color: "cyan" },
  { time: "12 MIN", title: "Design agent prepared a visual direction", detail: "Design Studio", color: "rose" },
];

const humanTeam = [
  { name: "Elango S", role: "Founder", initials: "ES" },
  { name: "Karmjit SG", role: "Co-founder", initials: "KS" },
  { name: "Prajith P", role: "Co-founder", initials: "PP" },
  { name: "Aaditya R M", role: "Founding Advisor", initials: "AR" },
  { name: "Vaishnavi M", role: "Tester", initials: "VM" },
  { name: "Meghana P Banda", role: "Tester", initials: "MB" },
  { name: "Dhakshatha S", role: "Developer · Social Media", initials: "DS" },
  { name: "Ishita Das", role: "Designer", initials: "ID" },
  { name: "Mohana Priya G", role: "Designer", initials: "MP" },
  { name: "Dhanusri T", role: "Tester · Developer", initials: "DT" },
  { name: "Gopika S", role: "Developer", initials: "GS" },
];

const roomLinks: { id: RoomKey; label: string; short: string; tint: string }[] = [
  { id: "all", label: "Entire office", short: "HQ", tint: "#D4DEEF" },
  { id: "command", label: "Command Hub", short: "CEO", tint: "#A78BFA" },
  { id: "development", label: "Development", short: "DEV", tint: "#22D3EE" },
  { id: "design", label: "Design Studio", short: "DES", tint: "#FB7185" },
  { id: "research", label: "Research Library", short: "RES", tint: "#FBBF24" },
  { id: "quality", label: "Quality Lab", short: "QA", tint: "#4ADE80" },
];

const navigation: { id: PanelKey; label: string; glyph: string; count?: string }[] = [
  { id: "agents", label: "Agents", glyph: "◉", count: "05" },
  { id: "tasks", label: "Missions", glyph: "▤", count: "03" },
  { id: "activity", label: "Activity", glyph: "⌁" },
  { id: "team", label: "People", glyph: "♧", count: "11" },
  { id: "approvals", label: "Approvals", glyph: "◇", count: "00" },
  { id: "settings", label: "Studio", glyph: "⚙" },
];

const panelTitles: Record<PanelKey, { eyebrow: string; title: string; subtitle: string }> = {
  agents: { eyebrow: "INTELLIGENCE NETWORK", title: "AI agents", subtitle: "Select a specialist to inspect its current assignment." },
  tasks: { eyebrow: "WORK IN MOTION", title: "Mission board", subtitle: "The work currently moving through SINC." },
  activity: { eyebrow: "LIVE SIGNAL", title: "Office activity", subtitle: "Recent events from the prototype workspace." },
  team: { eyebrow: "THE PEOPLE BEHIND SINC", title: "Our team", subtitle: "Human teammates and their current roles." },
  approvals: { eyebrow: "HUMAN CONTROL", title: "Approval queue", subtitle: "Privileged actions will appear here when the runtime is connected." },
  settings: { eyebrow: "WORKSPACE PREFERENCES", title: "Studio settings", subtitle: "Preview the visual identity and office controls." },
};

function statusClass(status: OfficeAgent["status"]) {
  return `agent-state-${status}`;
}

export function OfficeExperience() {
  const [theme, setTheme] = useState<BrandTheme>("cyber");
  const [agents] = useState(INITIAL_AGENTS);
  const [selectedAgentId, setSelectedAgentId] = useState("ceo");
  const [activePanel, setActivePanel] = useState<PanelKey>("agents");
  const [focusedRoom, setFocusedRoom] = useState<RoomKey>("all");
  const [showMap, setShowMap] = useState(false);
  const [panelOpen, setPanelOpen] = useState(true);
  const selectedAgent = useMemo(
    () => agents.find((agent) => agent.id === selectedAgentId) ?? agents[0],
    [agents, selectedAgentId],
  );
  const palette = BRAND_THEMES[theme];
  const panelMeta = panelTitles[activePanel];

  const choosePanel = (panel: PanelKey) => {
    if (activePanel === panel && panelOpen) {
      setPanelOpen(false);
      return;
    }
    setActivePanel(panel);
    setPanelOpen(true);
  };

  const cycleTheme = () => {
    setTheme((current) =>
      current === "cyber" ? "ember" : current === "ember" ? "indigo" : "cyber",
    );
  };

  return (
    <main className="sinc-world" data-theme={theme}>
      <div className="world-backdrop" />
      <div className="world-canvas" aria-label="Interactive AgentSINC 3D headquarters">
        {showMap ? (
          <OfficeMap2D
            agents={agents}
            selectedAgentId={selectedAgentId}
            onSelect={setSelectedAgentId}
            focusedRoom={focusedRoom}
            onFocusRoom={setFocusedRoom}
            onReturnTo3D={() => setShowMap(false)}
          />
        ) : (
          <OfficeViewport
            agents={agents}
            selectedAgentId={selectedAgentId}
            onSelectAgent={setSelectedAgentId}
            theme={theme}
            focusedRoom={focusedRoom}
          />
        )}
      </div>
      <div className="world-vignette" />

      <header className="world-topbar">
        <a className="world-brand" href="#home" aria-label="AgentSINC home">
          <span className="world-brand-mark"><img src={palette.mark} alt="" /></span>
          <span className="world-brand-type">
            <strong>Agent<span>SINC</span></strong>
            <small>INNOVATION · NETWORK · COLLABORATION</small>
          </span>
        </a>

        <div className="world-location">
          <span className="location-pulse" />
          <span>SINC HEADQUARTERS</span>
          <i />
          <strong>FLOOR 01</strong>
        </div>

        <div className="world-top-actions">
          <div className="runtime-indicator">
            <span className="runtime-indicator-dot" />
            <span>LOCAL PREVIEW</span>
          </div>
          <button className="theme-cycle" onClick={cycleTheme} title={`Current theme: ${palette.label}. Click to change.`}>
            <span className="theme-cycle-swatch" />
            <span>{palette.label}</span>
            <span className="theme-cycle-arrow">↗</span>
          </button>
          <button className="founder-avatar" title="Elango S · Founder">ES</button>
        </div>
      </header>

      <aside className="world-rail" aria-label="Workspace panels">
        <div className="rail-top-glyph">S</div>
        <div className="rail-divider" />
        {navigation.map((item) => (
          <button
            key={item.id}
            className={activePanel === item.id && panelOpen ? "rail-action active" : "rail-action"}
            onClick={() => choosePanel(item.id)}
            aria-label={item.label}
            aria-pressed={activePanel === item.id && panelOpen}
            title={item.label}
          >
            <span className="rail-action-glyph">{item.glyph}</span>
            {item.count ? <small>{item.count}</small> : null}
          </button>
        ))}
        <div className="rail-spacer" />
        <button className={showMap ? "rail-action active" : "rail-action"} onClick={() => setShowMap((value) => !value)} aria-label="Toggle floor map" title="Toggle floor map">
          <span className="rail-action-glyph">▦</span>
        </button>
        <div className="rail-foot-label">SINC / 01</div>
      </aside>

      <section className="world-intro">
        <p className="world-eyebrow"><span /> THE AUTONOMOUS COMPANY FLOOR</p>
        <h1>Welcome to<br /><em>SINC headquarters.</em></h1>
        <p className="world-intro-copy">A living workspace for people and intelligent teams.</p>
        <div className="world-intro-stats">
          <div><strong>05</strong><span>AI SPECIALISTS</span></div>
          <i />
          <div><strong>03</strong><span>ACTIVE MISSIONS</span></div>
        </div>
      </section>

      <section className="room-dock" aria-label="Office rooms">
        <span className="dock-label">EXPLORE FLOOR</span>
        <div className="room-dock-list">
          {roomLinks.map((room) => (
            <button
              key={room.id}
              className={focusedRoom === room.id ? "room-chip selected" : "room-chip"}
              style={{ "--room-tint": room.tint } as CSSProperties}
              onClick={() => {
                setFocusedRoom(room.id);
                setShowMap(false);
              }}
            >
              <span>{room.short}</span>
              <small>{room.label}</small>
            </button>
          ))}
        </div>
      </section>

      <div className="world-bottom-left">
        <span className="bottom-live-dot" />
        <span>ALL SYSTEMS IN PREVIEW MODE</span>
        <i />
        <span>SCENE 01 / HQ</span>
      </div>

      {panelOpen ? (
        <aside className="world-panel">
          <div className="world-panel-head">
            <div>
              <p className="world-eyebrow">{panelMeta.eyebrow}</p>
              <h2>{panelMeta.title}</h2>
              <p className="world-panel-subtitle">{panelMeta.subtitle}</p>
            </div>
            <button className="panel-close" onClick={() => setPanelOpen(false)} aria-label="Close panel">×</button>
          </div>

          {activePanel === "agents" ? (
            <AgentPanel
              agents={agents}
              selectedAgent={selectedAgent}
              selectedAgentId={selectedAgentId}
              onSelect={setSelectedAgentId}
            />
          ) : null}

          {activePanel === "tasks" ? (
            <div className="panel-content mission-list">
              {tasks.map((task) => (
                <article className="mission-card" key={task.id}>
                  <div className="mission-topline"><span>{task.id}</span><span className={task.status === "Review" ? "mission-status review" : "mission-status"}>{task.status}</span></div>
                  <h3>{task.title}</h3>
                  <p>{task.room} · {task.owner}</p>
                  <div className="mission-progress-copy"><span>Progress</span><strong>{task.progress}%</strong></div>
                  <div className="mission-progress"><i style={{ width: `${task.progress}%` }} /></div>
                </article>
              ))}
              <div className="panel-note">Preview assignments only. Live task management connects in the backend phase.</div>
            </div>
          ) : null}

          {activePanel === "activity" ? (
            <div className="panel-content signal-list">
              {activity.map((entry) => (
                <article className="signal-item" key={entry.title}>
                  <i className={`signal-dot ${entry.color}`} />
                  <div><small>{entry.time} · {entry.detail}</small><p>{entry.title}</p></div>
                </article>
              ))}
            </div>
          ) : null}

          {activePanel === "team" ? (
            <div className="panel-content team-list">
              {humanTeam.map((member) => (
                <div className="team-person" key={member.name}>
                  <span>{member.initials}</span>
                  <div><strong>{member.name}</strong><small>{member.role}</small></div>
                </div>
              ))}
            </div>
          ) : null}

          {activePanel === "approvals" ? (
            <div className="panel-empty">
              <span className="empty-symbol">◇</span>
              <strong>No approvals waiting</strong>
              <p>Human approval controls will be connected before agents can perform privileged actions.</p>
            </div>
          ) : null}

          {activePanel === "settings" ? (
            <div className="panel-content settings-list">
              <div className="setting-block">
                <span>BRAND IDENTITY</span>
                <strong>{palette.label}</strong>
                <div className="palette-options">
                  <button className={theme === "cyber" ? "palette-choice selected" : "palette-choice"} onClick={() => setTheme("cyber")}><i className="palette-cyber" /> Cyan / Violet</button>
                  <button className={theme === "ember" ? "palette-choice selected" : "palette-choice"} onClick={() => setTheme("ember")}><i className="palette-ember" /> Ember</button>
                  <button className={theme === "indigo" ? "palette-choice selected" : "palette-choice"} onClick={() => setTheme("indigo")}><i className="palette-indigo" /> Indigo / Lime</button>
                </div>
              </div>
              <div className="setting-block"><span>RENDER QUALITY</span><strong>Adaptive · Preview</strong><small>Quality presets and performance controls will be added after the scene profiling pass.</small></div>
              <div className="setting-block"><span>RUNTIME</span><strong>Local visual prototype</strong><small>No model, API, database or worker connection is active yet.</small></div>
            </div>
          ) : null}
        </aside>
      ) : (
        <button className="panel-reopen" onClick={() => setPanelOpen(true)}>OPEN {activePanel.toUpperCase()} <span>↗</span></button>
      )}

      <footer className="world-footer">
        <div className="footer-brand">AGENTSINC <span>·</span> SINC INTELLIGENCE</div>
        <div className="footer-shortcuts"><kbd>DRAG</kbd> ORBIT <i /> <kbd>SCROLL</kbd> ZOOM <i /> <kbd>CLICK</kbd> SELECT AGENT</div>
        <div className="footer-version">PHASE 2 / VISUAL BUILD</div>
      </footer>
    </main>
  );
}

function AgentPanel({
  agents,
  selectedAgent,
  selectedAgentId,
  onSelect,
}: {
  agents: OfficeAgent[];
  selectedAgent: OfficeAgent;
  selectedAgentId: string;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="panel-content">
      <div className="agent-feature">
        <div className="agent-feature-emblem" style={{ "--agent-color": selectedAgent.color } as CSSProperties}>
          <span>{selectedAgent.id === "ceo" ? "✳" : selectedAgent.name.slice(0, 1)}</span>
          <i />
        </div>
        <div className="agent-feature-copy">
          <h3>{selectedAgent.name}</h3>
          <p>{selectedAgent.role}</p>
          <span className={`agent-live-state ${statusClass(selectedAgent.status)}`}><i /> {STATUS_LABELS[selectedAgent.status]}</span>
        </div>
      </div>

      <div className="agent-detail-grid">
        <div><small>DEPARTMENT</small><strong>{selectedAgent.department}</strong></div>
        <div><small>AGENT TYPE</small><strong>{selectedAgent.model}</strong></div>
      </div>

      <div className="agent-current-mission">
        <div className="mission-section-heading"><span>CURRENT MISSION</span><b>{selectedAgent.progress}%</b></div>
        <p>{selectedAgent.currentTask}</p>
        <div className="mission-progress"><i style={{ width: `${selectedAgent.progress}%`, background: selectedAgent.color }} /></div>
      </div>

      <div className="panel-section-label">SPECIALIST NETWORK <span>05</span></div>
      <div className="specialist-list">
        {agents.map((agent) => (
          <button
            key={agent.id}
            className={agent.id === selectedAgentId ? "specialist-row selected" : "specialist-row"}
            onClick={() => onSelect(agent.id)}
            aria-pressed={agent.id === selectedAgentId}
          >
            <span className="specialist-avatar" style={{ "--agent-color": agent.color } as CSSProperties}>{agent.id === "ceo" ? "✳" : agent.name.slice(0, 1)}</span>
            <span className="specialist-copy"><strong>{agent.name}</strong><small>{agent.role}</small></span>
            <i className={`specialist-presence ${statusClass(agent.status)}`} />
          </button>
        ))}
      </div>
      <div className="panel-note">Agent profiles are sample data until the orchestration service is connected.</div>
    </div>
  );
}

function OfficeMap2D({
  agents,
  selectedAgentId,
  onSelect,
  focusedRoom,
  onFocusRoom,
  onReturnTo3D,
}: {
  agents: OfficeAgent[];
  selectedAgentId: string;
  onSelect: (id: string) => void;
  focusedRoom: RoomKey;
  onFocusRoom: (room: RoomKey) => void;
  onReturnTo3D: () => void;
}) {
  const positions = [
    { id: "command", x: "50%", y: "22%", label: "COMMAND HUB" },
    { id: "development", x: "23%", y: "43%", label: "DEVELOPMENT" },
    { id: "design", x: "77%", y: "43%", label: "DESIGN STUDIO" },
    { id: "research", x: "23%", y: "78%", label: "RESEARCH" },
    { id: "quality", x: "77%", y: "78%", label: "QUALITY LAB" },
  ];

  return (
    <div className="office-map">
      <div className="map-orbit map-orbit-one" />
      <div className="map-orbit map-orbit-two" />
      <div className="map-core">SINC<br /><small>OPERATIONS</small></div>
      {positions.map((position, index) => {
        const agent = agents[index];
        return (
          <button
            key={agent.id}
            className={agent.id === selectedAgentId ? "map-node selected" : "map-node"}
            style={{ left: position.x, top: position.y, "--agent-color": agent.color } as CSSProperties}
            onClick={() => { onSelect(agent.id); onFocusRoom(position.id as RoomKey); }}
          >
            <span>{agent.id === "ceo" ? "✳" : agent.name.slice(0, 1)}</span>
            <strong>{position.label}</strong>
            <small>{agent.role}</small>
          </button>
        );
      })}
      <div className="map-caption">FLOOR 01 · SELECT A DEPARTMENT TO EXPLORE</div>
      <button className="map-return-3d" onClick={onReturnTo3D}>RETURN TO 3D ↗</button>
    </div>
  );
}
