"use client";

import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
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
    <div className="scene-loading">
      <div className="loading-orbit" />
      <span>Preparing the SINC office…</span>
    </div>
  ),
});

const tasks = [
  {
    id: "AS-001",
    title: "Finalize AgentSINC product architecture",
    owner: "SINC CEO",
    status: "In progress",
    progress: 72,
    color: "violet",
  },
  {
    id: "AS-002",
    title: "Build the original 3D office prototype",
    owner: "Dev Agent",
    status: "In progress",
    progress: 64,
    color: "cyan",
  },
  {
    id: "AS-003",
    title: "Prepare the brand direction board",
    owner: "Design Agent",
    status: "Review",
    progress: 48,
    color: "rose",
  },
];

const activities = [
  { time: "Just now", text: "SINC CEO updated the company roadmap.", tone: "violet" },
  { time: "4 min ago", text: "Dev Agent started the office foundation task.", tone: "cyan" },
  { time: "12 min ago", text: "Design Agent shared a brand exploration.", tone: "rose" },
];

function statusClass(status: OfficeAgent["status"]) {
  return `status-${status}`;
}

export function OfficeExperience() {
  const [theme, setTheme] = useState<BrandTheme>("cyber");
  const [agents] = useState(INITIAL_AGENTS);
  const [selectedAgentId, setSelectedAgentId] = useState("ceo");
  const [show2d, setShow2d] = useState(false);

  const selectedAgent = useMemo(
    () => agents.find((agent) => agent.id === selectedAgentId) ?? agents[0],
    [agents, selectedAgentId],
  );
  const currentTheme = BRAND_THEMES[theme];

  return (
    <div className="app-shell" data-theme={theme}>
      <aside className="sidebar">
        <div className="brand-lockup">
          <div className="brand-symbol">
            <img src={currentTheme.mark} alt="" />
          </div>
          <div className="brand-copy">
            <strong>Agent<span>SINC</span></strong>
            <small>INNOVATION · NETWORK · COLLABORATION</small>
          </div>
        </div>

        <div className="workspace-switcher">
          <div className="workspace-avatar">S</div>
          <div>
            <strong>SINC Headquarters</strong>
            <span>Founder workspace</span>
          </div>
          <span className="switcher-chevron">⌄</span>
        </div>

        <nav className="primary-nav" aria-label="Main navigation">
          <p className="nav-section-label">WORKSPACE</p>
          <a className="nav-link active" href="#office">
            <span className="nav-icon">⌂</span>
            <span>3D Office</span>
            <span className="nav-pill">LIVE</span>
          </a>
          <a className="nav-link" href="#agents">
            <span className="nav-icon">◉</span>
            <span>AI Agents</span>
            <span className="nav-count">5</span>
          </a>
          <a className="nav-link" href="#tasks">
            <span className="nav-icon">▤</span>
            <span>Task Board</span>
          </a>
          <a className="nav-link" href="#activity">
            <span className="nav-icon">↗</span>
            <span>Activity</span>
          </a>

          <p className="nav-section-label nav-section-spaced">MANAGEMENT</p>
          <a className="nav-link" href="#team">
            <span className="nav-icon">♧</span>
            <span>SINC Team</span>
          </a>
          <a className="nav-link" href="#approvals">
            <span className="nav-icon">◇</span>
            <span>Approvals</span>
            <span className="nav-count pending-count">0</span>
          </a>
          <a className="nav-link" href="#settings">
            <span className="nav-icon">⚙</span>
            <span>Settings</span>
          </a>
        </nav>

        <div className="sidebar-bottom">
          <div className="runtime-card">
            <div className="runtime-card-top">
              <span className="live-dot" />
              <span>RUNTIME PREVIEW</span>
            </div>
            <strong>Local prototype</strong>
            <p>Sample data only. API and worker integration comes in later phases.</p>
          </div>
          <div className="user-chip">
            <div className="user-avatar">ES</div>
            <div className="user-copy">
              <strong>Elango S</strong>
              <span>Founder</span>
            </div>
            <span className="user-menu">···</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb">
            <span>SINC</span>
            <b>/</b>
            <strong>Headquarters</strong>
          </div>
          <div className="topbar-right">
            <div className="system-state">
              <span className="live-dot" />
              <span>OFFICE PREVIEW</span>
            </div>
            <div className="theme-switcher" aria-label="Brand palette preview">
              <span>BRAND</span>
              <button
                className={theme === "cyber" ? "theme-dot active" : "theme-dot"}
                onClick={() => setTheme("cyber")}
                aria-label="Use cyan and violet theme"
                title="Cyan + Violet"
              >
                A
              </button>
              <button
                className={theme === "ember" ? "theme-dot active" : "theme-dot"}
                onClick={() => setTheme("ember")}
                aria-label="Use ember theme"
                title="Ember"
              >
                B
              </button>
              <button
                className={theme === "indigo" ? "theme-dot active" : "theme-dot"}
                onClick={() => setTheme("indigo")}
                aria-label="Use indigo and lime theme"
                title="Indigo + Lime"
              >
                C
              </button>
            </div>
            <div className="date-chip">MON · 16 NOV 2026</div>
            <button className="topbar-avatar" aria-label="Founder profile">ES</button>
          </div>
        </header>

        <section className="welcome-row">
          <div>
            <p className="eyebrow">SINC INTELLIGENCE / COMPANY OPERATIONS</p>
            <h1>Your company, <span>in motion.</span></h1>
            <p className="welcome-description">
              A shared workspace where your AI team can plan, build, research and verify.
            </p>
          </div>
          <div className="welcome-note">
            <span className="note-icon">✳</span>
            <div>
              <strong>Built around your team</strong>
              <p>One company. One source of truth. Coordinated agents.</p>
            </div>
          </div>
        </section>

        <section className="metric-grid" aria-label="Office overview">
          <Metric label="AI AGENTS" value="05" detail="Specialist roles" icon="◉" />
          <Metric label="ACTIVE TASKS" value="03" detail="Across 4 departments" icon="▤" />
          <Metric label="COMPLETED TODAY" value="08" detail="Prototype activity" icon="✓" />
          <Metric label="PENDING APPROVALS" value="00" detail="Nothing waiting" icon="◇" />
        </section>

        <section className="office-layout" id="office">
          <div className="office-card">
            <div className="section-heading office-heading">
              <div>
                <div className="section-title-line">
                  <span className="eyebrow">VIRTUAL HEADQUARTERS</span>
                  <span className="scene-live-tag"><span className="live-dot" /> PREVIEW</span>
                </div>
                <h2>The SINC office</h2>
                <p>Explore the departments and select an agent to inspect its role.</p>
              </div>
              <div className="scene-controls">
                <button
                  className={show2d ? "view-toggle active" : "view-toggle"}
                  onClick={() => setShow2d(true)}
                >
                  2D
                </button>
                <button
                  className={!show2d ? "view-toggle active" : "view-toggle"}
                  onClick={() => setShow2d(false)}
                >
                  3D
                </button>
              </div>
            </div>

            <div className="office-viewport">
              {show2d ? (
                <OfficeMap2D agents={agents} selectedAgentId={selectedAgentId} onSelect={setSelectedAgentId} />
              ) : (
                <OfficeViewport
                  agents={agents}
                  selectedAgentId={selectedAgentId}
                  onSelectAgent={setSelectedAgentId}
                  theme={theme}
                />
              )}
              <div className="viewport-caption">
                <span><i className="legend-dot" /> Department zones</span>
                <span><i className="legend-agent" /> AI agent</span>
                <span className="viewport-hint">Drag to orbit · Scroll to zoom</span>
              </div>
            </div>
          </div>

          <aside className="agent-inspector" id="agents">
            <div className="inspector-header">
              <div>
                <p className="eyebrow">AGENT PROFILE</p>
                <h2>Team member</h2>
              </div>
              <span className="inspector-index">01 / 05</span>
            </div>

            <div className="selected-agent">
              <div className="agent-emblem" style={{ "--agent-color": selectedAgent.color } as React.CSSProperties}>
                <span>{selectedAgent.role === "Chief Orchestrator" ? "✳" : selectedAgent.name.slice(0, 1)}</span>
              </div>
              <div className="selected-agent-name">
                <h3>{selectedAgent.name}</h3>
                <p>{selectedAgent.role}</p>
                <span className={`agent-status ${statusClass(selectedAgent.status)}`}>
                  <i /> {STATUS_LABELS[selectedAgent.status]}
                </span>
              </div>
            </div>

            <div className="inspector-divider" />
            <InfoRow label="DEPARTMENT" value={selectedAgent.department} />
            <InfoRow label="RUNTIME PROFILE" value={selectedAgent.model} />
            <div className="current-task-block">
              <span className="eyebrow">CURRENT FOCUS</span>
              <p>{selectedAgent.currentTask}</p>
              <div className="progress-meta">
                <span>Task progress</span>
                <strong>{selectedAgent.progress}%</strong>
              </div>
              <div className="progress-track">
                <div style={{ width: `${selectedAgent.progress}%`, background: selectedAgent.color }} />
              </div>
            </div>
            <div className="agent-selector">
              <span className="eyebrow">SELECT ANOTHER AGENT</span>
              <div className="agent-selector-list">
                {agents.map((agent) => (
                  <button
                    key={agent.id}
                    className={agent.id === selectedAgentId ? "agent-mini selected" : "agent-mini"}
                    onClick={() => setSelectedAgentId(agent.id)}
                    aria-pressed={agent.id === selectedAgentId}
                  >
                    <span style={{ "--agent-color": agent.color } as React.CSSProperties}>{agent.name.slice(0, 1)}</span>
                    <small>{agent.role}</small>
                    <i className={statusClass(agent.status)} />
                  </button>
                ))}
              </div>
            </div>
          </aside>
        </section>

        <section className="lower-grid">
          <div className="data-card" id="tasks">
            <div className="section-heading compact-heading">
              <div>
                <p className="eyebrow">WORK IN MOTION</p>
                <h2>Active assignments</h2>
              </div>
              <span className="subtle-count">03 TASKS</span>
            </div>
            <div className="task-list">
              {tasks.map((task) => (
                <div className="task-row" key={task.id}>
                  <div className={`task-indicator ${task.color}`} />
                  <div className="task-copy">
                    <span>{task.id}</span>
                    <strong>{task.title}</strong>
                    <small>Assigned to {task.owner}</small>
                  </div>
                  <div className="task-progress">
                    <strong>{task.progress}%</strong>
                    <div className="progress-track"><div style={{ width: `${task.progress}%` }} /></div>
                  </div>
                  <span className={task.status === "Review" ? "task-status review" : "task-status"}>
                    {task.status}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="data-card activity-card" id="activity">
            <div className="section-heading compact-heading">
              <div>
                <p className="eyebrow">LIVE FEED</p>
                <h2>Recent activity</h2>
              </div>
              <span className="activity-signal"><i /> PREVIEW</span>
            </div>
            <div className="activity-list">
              {activities.map((activity, index) => (
                <div className="activity-row" key={activity.text}>
                  <span className={`activity-marker ${activity.tone}`} />
                  <div>
                    <p>{activity.text}</p>
                    <small>{activity.time}</small>
                  </div>
                  {index === 0 ? <span className="new-tag">NEW</span> : null}
                </div>
              ))}
            </div>
          </div>
        </section>

        <footer className="page-footer">
          <span>AGENTSINC <b>·</b> PHASE 2 UI PROTOTYPE</span>
          <span>Sample data only · API, authentication and worker are not connected yet</span>
        </footer>
      </main>
    </div>
  );
}

function Metric({
  label,
  value,
  detail,
  icon,
}: {
  label: string;
  value: string;
  detail: string;
  icon: string;
}) {
  return (
    <article className="metric-card">
      <div className="metric-top">
        <span>{label}</span>
        <i>{icon}</i>
      </div>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="info-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function OfficeMap2D({
  agents,
  selectedAgentId,
  onSelect,
}: {
  agents: OfficeAgent[];
  selectedAgentId: string;
  onSelect: (id: string) => void;
}) {
  const positions = [
    { x: "50%", y: "22%", label: "COMMAND HUB" },
    { x: "22%", y: "43%", label: "DEVELOPMENT" },
    { x: "78%", y: "43%", label: "DESIGN STUDIO" },
    { x: "22%", y: "77%", label: "RESEARCH" },
    { x: "78%", y: "77%", label: "QUALITY LAB" },
  ];

  return (
    <div className="office-map-2d">
      <div className="map-grid" />
      <div className="map-center-label">SINC HQ · FLOOR 01</div>
      {agents.map((agent, index) => {
        const position = positions[index];
        return (
          <button
            key={agent.id}
            className={agent.id === selectedAgentId ? "map-agent selected" : "map-agent"}
            style={{
              left: position.x,
              top: position.y,
              "--agent-color": agent.color,
            } as React.CSSProperties}
            onClick={() => onSelect(agent.id)}
          >
            <span>{agent.name.slice(0, 1)}</span>
            <strong>{agent.role}</strong>
            <small>{position.label}</small>
          </button>
        );
      })}
      <div className="map-corridor" />
    </div>
  );
}
