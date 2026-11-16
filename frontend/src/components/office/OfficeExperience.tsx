"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState, type CSSProperties, type FormEvent } from "react";
import {
  BRAND_THEMES,
  INITIAL_AGENTS,
  STATUS_LABELS,
  type BrandTheme,
  type OfficeAgent,
} from "./types";
import {
  cancelMission,
  cancelOrchestration,
  chooseLocalModel,
  controlAgent,
  createMission,
  createOrchestration,
  getOverview,
  getWorkspaceSummary,
  retryMission,
  type AgentEvent,
  type AgentOrchestration,
  type AgentTask,
  type RuntimeStatus,
  type WorkspaceSummary,
} from "@/lib/agentsinc-api";

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

const navigation: { id: PanelKey; label: string; glyph: string }[] = [
  { id: "agents", label: "Agents", glyph: "◉" },
  { id: "tasks", label: "Missions", glyph: "▤" },
  { id: "activity", label: "Activity", glyph: "⌁" },
  { id: "team", label: "People", glyph: "♧" },
  { id: "approvals", label: "Approvals", glyph: "◇" },
  { id: "settings", label: "Studio", glyph: "⚙" },
];

const panelTitles: Record<PanelKey, { eyebrow: string; title: string; subtitle: string }> = {
  agents: { eyebrow: "INTELLIGENCE NETWORK", title: "Agent control", subtitle: "Inspect assignments, event history and availability." },
  tasks: { eyebrow: "WORK IN MOTION", title: "Mission board", subtitle: "Persistent missions stored by the local runtime." },
  activity: { eyebrow: "LIVE SIGNAL", title: "Office activity", subtitle: "Timestamped events emitted by the API and worker." },
  team: { eyebrow: "THE PEOPLE BEHIND SINC", title: "Our team", subtitle: "Human teammates and their current roles." },
  approvals: { eyebrow: "HUMAN CONTROL", title: "Approval queue", subtitle: "External actions remain disabled until an approval system is implemented." },
  settings: { eyebrow: "LOCAL RUNTIME", title: "Studio settings", subtitle: "Inspect Ollama, worker health and the selected local model." },
};

const disconnectedRuntime: RuntimeStatus = {
  api_connected: false,
  worker_online: false,
  worker_state: "stopped",
  worker_heartbeat: null,
  ollama_online: false,
  models: [],
  selected_model: null,
  zero_cost_mode: true,
  execution_mode: "local-ollama",
};

function statusClass(status: OfficeAgent["status"]) {
  return `agent-state-${status}`;
}

function formatTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown time";
  return date.toLocaleString([], {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatTaskStatus(status: AgentTask["status"]) {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export function OfficeExperience() {
  const [theme, setTheme] = useState<BrandTheme>("cyber");
  const [agents, setAgents] = useState<OfficeAgent[]>(INITIAL_AGENTS);
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [orchestrations, setOrchestrations] = useState<AgentOrchestration[]>([]);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [runtime, setRuntime] = useState<RuntimeStatus>(disconnectedRuntime);
  const [runtimeError, setRuntimeError] = useState("Start the local API and worker to enable real agent work.");
  const [selectedAgentId, setSelectedAgentId] = useState("ceo");
  const [activePanel, setActivePanel] = useState<PanelKey>("agents");
  const [focusedRoom, setFocusedRoom] = useState<RoomKey>("all");
  const [showMap, setShowMap] = useState(false);
  const [panelOpen, setPanelOpen] = useState(true);
  const [missionTitle, setMissionTitle] = useState("");
  const [missionInstructions, setMissionInstructions] = useState("");
  const [busyAction, setBusyAction] = useState("");
  const [notice, setNotice] = useState("");
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null);
  const [expandedOrchestrationId, setExpandedOrchestrationId] = useState<string | null>(null);

  const selectedAgent = useMemo(
    () => agents.find((agent) => agent.id === selectedAgentId) ?? agents[0],
    [agents, selectedAgentId],
  );
  const palette = BRAND_THEMES[theme];
  const panelMeta = panelTitles[activePanel];
  const activeMissionCount = tasks.filter((task) => task.status === "queued" || task.status === "running").length;
  const activeOrchestrationCount = orchestrations.filter((item) => item.status === "queued" || item.status === "running").length;
  const runningAgentCount = agents.filter((agent) => agent.status === "working" || agent.status === "thinking" || agent.status === "collaborating").length;
  const runtimeReady = runtime.api_connected && runtime.worker_online && runtime.ollama_online;
  const runtimeLabel = !runtime.api_connected
    ? "API OFFLINE"
    : !runtime.worker_online
      ? "WORKER OFFLINE"
      : !runtime.ollama_online
        ? "OLLAMA OFFLINE"
        : "LOCAL AGENTS ONLINE";

  const refreshOverview = async () => {
    try {
      const snapshot = await getOverview();
      setAgents(snapshot.agents);
      setTasks(snapshot.tasks);
      setOrchestrations(snapshot.orchestrations ?? []);
      setEvents(snapshot.events);
      setRuntime(snapshot.runtime);
      setRuntimeError("");
    } catch (error) {
      setRuntime(disconnectedRuntime);
      setRuntimeError(error instanceof Error ? error.message : "Local runtime is unavailable.");
      setAgents(INITIAL_AGENTS);
      setTasks([]);
      setOrchestrations([]);
      setEvents([]);
    }
  };

  useEffect(() => {
    let disposed = false;
    let inFlight = false;

    const refresh = async () => {
      if (inFlight || disposed) return;
      inFlight = true;
      try {
        const snapshot = await getOverview();
        if (!disposed) {
          setAgents(snapshot.agents);
          setTasks(snapshot.tasks);
          setOrchestrations(snapshot.orchestrations ?? []);
          setEvents(snapshot.events);
          setRuntime(snapshot.runtime);
          setRuntimeError("");
        }
      } catch (error) {
        if (!disposed) {
          setRuntime(disconnectedRuntime);
          setRuntimeError(error instanceof Error ? error.message : "Local runtime is unavailable.");
          setAgents(INITIAL_AGENTS);
          setTasks([]);
          setOrchestrations([]);
          setEvents([]);
        }
      } finally {
        inFlight = false;
      }
    };

    void refresh();
    const timer = window.setInterval(() => void refresh(), 2500);
    return () => {
      disposed = true;
      window.clearInterval(timer);
    };
  }, []);

  const choosePanel = (panel: PanelKey) => {
    if (activePanel === panel && panelOpen) {
      setPanelOpen(false);
      return;
    }
    setActivePanel(panel);
    setPanelOpen(true);
  };

  const selectAgent = (agentId: string) => {
    setSelectedAgentId(agentId);
    setActivePanel("agents");
    setPanelOpen(true);
    setShowMap(false);
  };

  const cycleTheme = () => {
    setTheme((current) => current === "cyber" ? "ember" : current === "ember" ? "indigo" : "cyber");
  };

  const assignMission = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedAgent || !missionTitle.trim() || !missionInstructions.trim()) return;
    setBusyAction("assign");
    setNotice("");
    try {
      if (selectedAgent.id === "ceo") {
        const response = await createOrchestration({
          title: missionTitle.trim(),
          instructions: missionInstructions.trim(),
        });
        setNotice(`CEO accepted the request and created orchestration ${response.orchestration.id.slice(0, 8)}.`);
      } else {
        await createMission({
          agent_id: selectedAgent.id,
          title: missionTitle.trim(),
          instructions: missionInstructions.trim(),
        });
        setNotice("Mission saved to the local queue.");
      }
      setMissionTitle("");
      setMissionInstructions("");
      await refreshOverview();
      setActivePanel("tasks");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not assign the mission.");
    } finally {
      setBusyAction("");
    }
  };

  const toggleAgent = async (agent: OfficeAgent) => {
    const action = agent.status === "paused" ? "resume" : "pause";
    setBusyAction(`agent-${agent.id}`);
    setNotice("");
    try {
      const result = await controlAgent(agent.id, action);
      setNotice(result.message);
      await refreshOverview();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Agent control failed.");
    } finally {
      setBusyAction("");
    }
  };

  const cancelTask = async (task: AgentTask) => {
    setBusyAction(`cancel-${task.id}`);
    setNotice("");
    try {
      await cancelMission(task.id);
      setNotice(task.status === "queued" ? "Queued mission cancelled." : "Cancellation requested; the worker is stopping generation.");
      await refreshOverview();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not cancel the mission.");
    } finally {
      setBusyAction("");
    }
  };

  const cancelOrchestrationRequest = async (orchestration: AgentOrchestration) => {
    setBusyAction(`orchestration-${orchestration.id}`);
    setNotice("");
    try {
      await cancelOrchestration(orchestration.id);
      setNotice("CEO orchestration cancellation requested.");
      await refreshOverview();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not cancel the CEO request.");
    } finally {
      setBusyAction("");
    }
  };

  const retryTask = async (task: AgentTask) => {
    setBusyAction(`retry-${task.id}`);
    setNotice("");
    try {
      await retryMission(task.id);
      setNotice("Mission added back to the local queue.");
      await refreshOverview();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not retry the mission.");
    } finally {
      setBusyAction("");
    }
  };

  const setModel = async (model: string) => {
    if (!model) return;
    setBusyAction("model");
    setNotice("");
    try {
      await chooseLocalModel(model);
      setNotice(`Local model changed to ${model}.`);
      await refreshOverview();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not select this model.");
    } finally {
      setBusyAction("");
    }
  };

  return (
    <main className="sinc-world" data-theme={theme}>
      <div className="world-backdrop" />
      <div className="world-canvas" aria-label="Interactive AgentSINC 3D headquarters">
        {showMap ? (
          <OfficeMap2D
            agents={agents}
            selectedAgentId={selectedAgentId}
            onSelect={selectAgent}
            focusedRoom={focusedRoom}
            onFocusRoom={setFocusedRoom}
            onReturnTo3D={() => setShowMap(false)}
          />
        ) : (
          <OfficeViewport
            agents={agents}
            selectedAgentId={selectedAgentId}
            onSelectAgent={selectAgent}
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
          <div className={runtimeReady ? "runtime-indicator ready" : "runtime-indicator disconnected"}>
            <span className="runtime-indicator-dot" />
            <span>{runtimeLabel}</span>
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
            {item.id === "agents" ? <small>{agents.length.toString().padStart(2, "0")}</small> : null}
            {item.id === "tasks" ? <small>{activeMissionCount.toString().padStart(2, "0")}</small> : null}
            {item.id === "team" ? <small>11</small> : null}
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
        <p className="world-intro-copy">Track local AI work, missions and agent activity in one place.</p>
        <div className="world-intro-stats">
          <div><strong>{agents.length.toString().padStart(2, "0")}</strong><span>AI SPECIALISTS</span></div>
          <i />
          <div><strong>{(activeMissionCount + activeOrchestrationCount).toString().padStart(2, "0")}</strong><span>OPEN MISSIONS</span></div>
          <i />
          <div><strong>{runningAgentCount.toString().padStart(2, "0")}</strong><span>ACTIVE AGENTS</span></div>
        </div>
        {!runtime.api_connected ? (
          <div className="runtime-warning">
            <strong>Local runtime not connected</strong>
            <span>Start the API and worker to assign missions and record activity.</span>
          </div>
        ) : null}
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
        <span className={runtimeReady ? "bottom-live-dot" : "bottom-live-dot offline"} />
        <span>{runtimeReady ? "LOCAL WORKER AND MODEL ONLINE" : runtime.api_connected ? "LOCAL RUNTIME PARTIALLY READY" : "LOCAL RUNTIME DISCONNECTED"}</span>
        <i />
        <span>MISSIONS SAVED LOCALLY</span>
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
              events={events.filter((event) => event.agent_id === selectedAgentId)}
              runtime={runtime}
              missionTitle={missionTitle}
              missionInstructions={missionInstructions}
              setMissionTitle={setMissionTitle}
              setMissionInstructions={setMissionInstructions}
              onSelect={selectAgent}
              onControl={toggleAgent}
              onAssign={assignMission}
              busyAction={busyAction}
              notice={notice}
            />
          ) : null}

          {activePanel === "tasks" ? (
            <MissionPanel
              tasks={tasks}
              agents={agents}
              expandedTaskId={expandedTaskId}
              onExpand={setExpandedTaskId}
              onCancel={cancelTask}
              onRetry={retryTask}
              orchestrations={orchestrations}
              expandedOrchestrationId={expandedOrchestrationId}
              onExpandOrchestration={setExpandedOrchestrationId}
              onCancelOrchestration={cancelOrchestrationRequest}
              busyAction={busyAction}
              onNewMission={() => {
                setActivePanel("agents");
                setPanelOpen(true);
              }}
            />
          ) : null}

          {activePanel === "activity" ? (
            <ActivityPanel events={events} agents={agents} />
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
              <strong>No external tools are enabled</strong>
              <p>File edits, repository writes, deployments and messages are intentionally disabled until the isolated execution sandbox and human approval flow are implemented.</p>
            </div>
          ) : null}

          {activePanel === "settings" ? (
            <SettingsPanel
              runtime={runtime}
              runtimeError={runtimeError}
              busyAction={busyAction}
              onSelectModel={setModel}
              onRefresh={() => void refreshOverview()}
              notice={notice}
            />
          ) : null}
        </aside>
      ) : (
        <button className="panel-reopen" onClick={() => setPanelOpen(true)}>OPEN {activePanel.toUpperCase()} <span>↗</span></button>
      )}

      <footer className="world-footer">
        <div className="footer-brand">AGENTSINC <span>·</span> SINC INTELLIGENCE</div>
        <div className="footer-shortcuts"><kbd>DRAG</kbd> ORBIT <i /> <kbd>SCROLL</kbd> ZOOM <i /> <kbd>CLICK</kbd> TRACK AGENT</div>
        <div className="footer-version">LOCAL CEO ORCHESTRATION / PHASE 4B</div>
      </footer>
    </main>
  );
}

function AgentPanel({
  agents,
  selectedAgent,
  selectedAgentId,
  events,
  runtime,
  missionTitle,
  missionInstructions,
  setMissionTitle,
  setMissionInstructions,
  onSelect,
  onControl,
  onAssign,
  busyAction,
  notice,
}: {
  agents: OfficeAgent[];
  selectedAgent: OfficeAgent;
  selectedAgentId: string;
  events: AgentEvent[];
  runtime: RuntimeStatus;
  missionTitle: string;
  missionInstructions: string;
  setMissionTitle: (value: string) => void;
  setMissionInstructions: (value: string) => void;
  onSelect: (id: string) => void;
  onControl: (agent: OfficeAgent) => void;
  onAssign: (event: FormEvent<HTMLFormElement>) => void;
  busyAction: string;
  notice: string;
}) {
  const isPaused = selectedAgent.paused === true || selectedAgent.status === "paused";
  const latestEvents = events.slice(0, 7);
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
        <div className="agent-control-row">
          <button className={isPaused ? "runtime-action primary" : "runtime-action"} onClick={() => onControl(selectedAgent)} disabled={busyAction === `agent-${selectedAgent.id}` || !runtime.api_connected}>
            {busyAction === `agent-${selectedAgent.id}` ? "Saving…" : isPaused ? "Resume agent" : "Pause agent"}
          </button>
          <span>{selectedAgent.paused ? "New missions paused" : "Accepting missions"}</span>
        </div>
      </div>

      <form className="mission-form" onSubmit={onAssign}>
        <div className="panel-section-label">{selectedAgent.id === "ceo" ? "SEND REQUEST TO CEO" : "ASSIGN A NEW MISSION"} <span>LOCAL AI</span></div>
        <label htmlFor="mission-title">Mission title</label>
        <input
          id="mission-title"
          value={missionTitle}
          onChange={(event) => setMissionTitle(event.target.value)}
          placeholder={selectedAgent.id === "ceo" ? "Describe the outcome you want the CEO to coordinate" : `Give ${selectedAgent.name} a task`}
          minLength={3}
          maxLength={120}
          required
        />
        <label htmlFor="mission-instructions">Instructions</label>
        <textarea
          id="mission-instructions"
          value={missionInstructions}
          onChange={(event) => setMissionInstructions(event.target.value)}
          placeholder="Describe the outcome, context and constraints…"
          rows={4}
          minLength={selectedAgent.id === "ceo" ? 20 : 10}
          maxLength={12000}
          required
        />
        <button className="runtime-action primary full" type="submit" disabled={!runtime.api_connected || busyAction === "assign" || isPaused}>
          {busyAction === "assign" ? "Submitting…" : selectedAgent.id === "ceo" ? "Send request to CEO" : "Assign mission to agent"}
        </button>
        {!runtime.api_connected ? <small className="form-hint">Start the local API to enable assignment.</small> : null}
        {runtime.api_connected && (!runtime.worker_online || !runtime.ollama_online) ? <small className="form-hint">Mission can queue now; start Ollama and the worker to process it.</small> : null}
        <small className="form-hint">{selectedAgent.id === "ceo" ? "CEO plans the request, delegates specialist missions, waits for their reports and prepares one consolidated response." : "The local model returns analysis and text deliverables. It cannot edit files or use external tools yet."}</small>
      </form>

      <div className="panel-section-label">AGENT TIMELINE <span>{events.length.toString().padStart(2, "0")}</span></div>
      <div className="agent-timeline">
        {latestEvents.length ? latestEvents.map((event) => (
          <article className="timeline-event" key={event.id}>
            <i />
            <div><p>{event.message}</p><small>{formatTime(event.created_at)}</small></div>
          </article>
        )) : <div className="panel-note">No activity has been recorded for this agent yet. Assign a mission to create the first timeline event.</div>}
      </div>

      <div className="panel-section-label">SPECIALIST NETWORK <span>{agents.length.toString().padStart(2, "0")}</span></div>
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
      {notice ? <div className="runtime-notice">{notice}</div> : null}
    </div>
  );
}

function MissionPanel({
  tasks,
  agents,
  expandedTaskId,
  onExpand,
  onCancel,
  onRetry,
  orchestrations,
  expandedOrchestrationId,
  onExpandOrchestration,
  onCancelOrchestration,
  busyAction,
  onNewMission,
}: {
  tasks: AgentTask[];
  agents: OfficeAgent[];
  expandedTaskId: string | null;
  onExpand: (id: string | null) => void;
  onCancel: (task: AgentTask) => void;
  onRetry: (task: AgentTask) => void;
  orchestrations: AgentOrchestration[];
  expandedOrchestrationId: string | null;
  onExpandOrchestration: (id: string | null) => void;
  onCancelOrchestration: (orchestration: AgentOrchestration) => void;
  busyAction: string;
  onNewMission: () => void;
}) {
  const agentNames = new Map(agents.map((agent) => [agent.id, agent.name]));
  return (
    <div className="panel-content mission-list">
      <button className="runtime-action primary full" onClick={onNewMission}>+ Assign a mission</button>
      {orchestrations.length ? (
        <>
          <div className="panel-section-label">CEO ORCHESTRATIONS <span>{orchestrations.length.toString().padStart(2, "0")}</span></div>
          {orchestrations.map((item) => {
            const active = item.status === "queued" || item.status === "running";
            const expanded = expandedOrchestrationId === item.id;
            return (
              <article className="mission-card" key={item.id}>
                <div className="mission-topline">
                  <span>CEO · {item.id.slice(0, 8).toUpperCase()}</span>
                  <span className={`mission-status status-${item.status === "running" ? "running" : item.status}`}>{item.stage}</span>
                </div>
                <h3>{item.title}</h3>
                <p>{item.tasks.length} specialist missions · {formatTime(item.created_at)}</p>
                {item.plan?.summary ? <p>{item.plan.summary}</p> : null}
                <div className="mission-progress-copy"><span>Workflow progress</span><strong>{item.progress}%</strong></div>
                <div className="mission-progress"><i style={{ width: `${item.progress}%` }} /></div>
                {item.tasks.length ? (
                  <div className="orchestration-children">
                    {item.tasks.map((child) => (
                      <div className="orchestration-child" key={child.id}>
                        <span>{agentNames.get(child.agent_id) ?? child.agent_id}</span>
                        <small>{child.title}</small>
                        <b className={`mission-status status-${child.status}`}>{child.status}</b>
                      </div>
                    ))}
                  </div>
                ) : null}
                <div className="mission-actions">
                  <button className="text-action" onClick={() => onExpandOrchestration(expanded ? null : item.id)}>
                    {expanded ? "Hide CEO report" : item.result ? "View CEO report" : "View request"}
                  </button>
                  {active ? (
                    <button className="text-action danger" onClick={() => onCancelOrchestration(item)} disabled={busyAction === `orchestration-${item.id}`}>
                      {busyAction === `orchestration-${item.id}` ? "Stopping…" : "Cancel"}
                    </button>
                  ) : null}
                </div>
                {expanded ? (
                  <div className="mission-detail">
                    <strong>Founder request</strong>
                    <p>{item.instructions}</p>
                    {item.error ? <><strong>Workflow error</strong><p className="task-error">{item.error}</p></> : null}
                    {item.result ? <><strong>CEO consolidated report</strong><pre>{item.result}</pre></> : null}
                    {!item.result && !item.error ? <small>CEO is working through the plan and specialist handoffs.</small> : null}
                  </div>
                ) : null}
              </article>
            );
          })}
        </>
      ) : null}
      {tasks.length ? tasks.map((task) => (
        <article className="mission-card" key={task.id}>
          <div className="mission-topline">
            <span>{task.id.slice(0, 8).toUpperCase()}</span>
            <span className={`mission-status status-${task.status}`}>{formatTaskStatus(task.status)}</span>
          </div>
          <h3>{task.title}</h3>
          <p>{agentNames.get(task.agent_id) ?? task.agent_id} · Created {formatTime(task.created_at)}</p>
          <div className="mission-progress-copy"><span>{task.status === "running" ? "Model response progress" : "Progress"}</span><strong>{task.progress}%</strong></div>
          <div className="mission-progress"><i style={{ width: `${task.progress}%` }} /></div>
          <div className="mission-actions">
            <button className="text-action" onClick={() => onExpand(expandedTaskId === task.id ? null : task.id)}>
              {expandedTaskId === task.id ? "Hide details" : "View details"}
            </button>
            {task.status === "queued" || task.status === "running" ? (
              <button className="text-action danger" onClick={() => onCancel(task)} disabled={busyAction === `cancel-${task.id}`}>
                {busyAction === `cancel-${task.id}` ? "Stopping…" : "Cancel"}
              </button>
            ) : null}
            {task.status === "failed" || task.status === "cancelled" ? (
              <button className="text-action" onClick={() => onRetry(task)} disabled={busyAction === `retry-${task.id}`}>
                {busyAction === `retry-${task.id}` ? "Retrying…" : "Retry"}
              </button>
            ) : null}
          </div>
          {expandedTaskId === task.id ? (
            <div className="mission-detail">
              <strong>Instructions</strong>
              <p>{task.instructions}</p>
              {task.error ? <><strong>Runtime error</strong><p className="task-error">{task.error}</p></> : null}
              {task.result ? <><strong>Agent deliverable</strong><pre>{task.result}</pre></> : null}
              {!task.result && !task.error ? <small>The agent has not produced a final deliverable yet.</small> : null}
            </div>
          ) : null}
        </article>
      )) : !orchestrations.length ? (
        <div className="panel-empty compact">
          <span className="empty-symbol">▤</span>
          <strong>No missions yet</strong>
          <p>Assign a mission to a specialist. It will be stored locally and picked up by the background worker.</p>
          <button className="runtime-action primary" onClick={onNewMission}>Create first mission</button>
        </div>
      ) : null}
    </div>
  );
}

function ActivityPanel({ events, agents }: { events: AgentEvent[]; agents: OfficeAgent[] }) {
  const agentNames = new Map(agents.map((agent) => [agent.id, agent.name]));
  return (
    <div className="panel-content signal-list">
      {events.length ? events.map((event) => (
        <article className="signal-item" key={event.id}>
          <i className="signal-dot" />
          <div>
            <small>{formatTime(event.created_at)} · {agentNames.get(event.agent_id) ?? event.agent_id}</small>
            <p>{event.message}</p>
            {event.task_id ? <span className="event-task-ref">MISSION {event.task_id.slice(0, 8).toUpperCase()}</span> : null}
          </div>
        </article>
      )) : <div className="panel-empty compact"><strong>No recorded activity</strong><p>Events appear here when the API or background worker changes agent or mission state.</p></div>}
    </div>
  );
}

function SettingsPanel({
  runtime,
  runtimeError,
  busyAction,
  onSelectModel,
  onRefresh,
  notice,
}: {
  runtime: RuntimeStatus;
  runtimeError: string;
  busyAction: string;
  onSelectModel: (model: string) => void;
  onRefresh: () => void;
  notice: string;
}) {
  const [workspace, setWorkspace] = useState<WorkspaceSummary | null>(null);
  const [workspaceLoading, setWorkspaceLoading] = useState(true);
  const [workspaceError, setWorkspaceError] = useState("");

  useEffect(() => {
    let disposed = false;
    getWorkspaceSummary()
      .then((summary) => {
        if (!disposed) {
          setWorkspace(summary);
          setWorkspaceError("");
        }
      })
      .catch((error: unknown) => {
        if (!disposed) {
          setWorkspaceError(error instanceof Error ? error.message : "Workspace inspection is unavailable.");
        }
      })
      .finally(() => {
        if (!disposed) setWorkspaceLoading(false);
      });
    return () => { disposed = true; };
  }, []);

  return (
    <div className="panel-content settings-list">

      <div className="runtime-health-card">
        <div className="runtime-health-head">
          <strong>PROJECT WORKSPACE</strong>
          <span className={workspace?.available ? "health-chip ready" : "health-chip"}>{workspaceLoading ? "CHECKING" : workspace?.available ? "READ ONLY" : "UNAVAILABLE"}</span>
        </div>
        {workspaceLoading ? <small>Inspecting the configured local project…</small> : null}
        {workspace ? (
          <>
            <div className="health-row"><i className="health-dot online" /><span>{workspace.root_name}</span><small>{workspace.file_count.toLocaleString()} text files</small></div>
            <small>Path-confined source access · dependency and secret folders excluded</small>
          </>
        ) : null}
        {workspaceError ? <small>{workspaceError}</small> : null}
      </div>
      <div className="runtime-health-card">
        <div className="runtime-health-head">
          <strong>LOCAL RUNTIME HEALTH</strong>
          <span className={runtime.api_connected && runtime.worker_online && runtime.ollama_online ? "health-chip ready" : "health-chip"}>{runtime.api_connected && runtime.worker_online && runtime.ollama_online ? "READY" : "CHECK SETUP"}</span>
        </div>
        <HealthRow label="FastAPI" online={runtime.api_connected} detail={runtime.api_connected ? "Connected" : "Not connected"} />
        <HealthRow label="Background worker" online={runtime.worker_online} detail={runtime.worker_online ? "Heartbeat active" : "Heartbeat missing"} />
        <HealthRow label="Ollama" online={runtime.ollama_online} detail={runtime.ollama_online ? "Local model service online" : "Local model service offline"} />
        <small>Local-only mode · no paid model API</small>
      </div>

      <div className="setting-block">
        <span>LOCAL MODEL</span>
        <strong>{runtime.selected_model ?? "No model selected"}</strong>
        <select
          className="runtime-model-select"
          value={runtime.selected_model ?? ""}
          onChange={(event) => onSelectModel(event.target.value)}
          disabled={!runtime.ollama_online || !runtime.models.length || busyAction === "model"}
        >
          <option value="">Choose installed model</option>
          {runtime.models.map((model) => <option value={model} key={model}>{model}</option>)}
        </select>
        <small>Only models already installed on this computer are listed. Selecting a model does not download anything.</small>
      </div>

      <div className="setting-block">
        <span>WORKER HEARTBEAT</span>
        <strong>{runtime.worker_heartbeat ? formatTime(runtime.worker_heartbeat) : "Not received"}</strong>
        <small>The office refreshes runtime information every 2.5 seconds. The worker continues when the browser is closed.</small>
      </div>

      <div className="setting-block">
        <span>ZERO-COST MODE</span>
        <strong>Local Ollama + SQLite</strong>
        <small>No cloud inference calls, PostgreSQL plan or Redis subscription in this local MVP. Your PC must stay awake and powered for continuous work.</small>
      </div>

      <button className="runtime-action full" onClick={onRefresh} disabled={busyAction.length > 0}>Refresh runtime status</button>
      {runtimeError ? <div className="runtime-notice">{runtimeError}</div> : null}
      {notice ? <div className="runtime-notice">{notice}</div> : null}
      <div className="panel-note">Code execution, file edits, browser automation and external actions are disabled until the isolated sandbox and approval controls are built.</div>
    </div>
  );
}

function HealthRow({ label, online, detail }: { label: string; online: boolean; detail: string }) {
  return (
    <div className="health-row">
      <i className={online ? "health-dot online" : "health-dot"} />
      <span>{label}</span>
      <small>{detail}</small>
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
            <small>{STATUS_LABELS[agent.status]}</small>
          </button>
        );
      })}
      <div className="map-caption">FLOOR 01 · SELECT A DEPARTMENT TO EXPLORE</div>
      <button className="map-return-3d" onClick={onReturnTo3D}>RETURN TO 3D ↗</button>
    </div>
  );
}
