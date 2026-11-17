export type AgentStatus =
  | "working"
  | "thinking"
  | "collaborating"
  | "idle"
  | "waiting"
  | "queued"
  | "paused"
  | "failed";

export type BrandTheme = "cyber" | "ember" | "indigo";

export type OfficeAgent = {
  id: string;
  name: string;
  role: string;
  department: string;
  status: AgentStatus;
  currentTask: string;
  progress: number;
  color: string;
  model: string;
  position: [number, number, number];
  /** Current destination derived from the persisted backend workflow state. */
  location?: "desk" | "command" | "discussion" | "meeting";
  /** Most recent persisted event for this agent, rendered on its physical monitor. */
  latestActivity?: string;
  /** Status of the most recent task, including the last completed task while idle. */
  taskStatus?: "queued" | "running" | "completed" | "failed" | "cancelled";
  /** Actual latest task result/error. Never replaced with a generated activity placeholder. */
  latestResult?: string | null;
  latestTaskUpdatedAt?: string | null;
  paused?: boolean;
};

export const BRAND_THEMES: Record<
  BrandTheme,
  { label: string; accent: string; secondary: string; floor: string; mark: string }
> = {
  cyber: {
    label: "Ocean + Orchid",
    accent: "#2676E8",
    secondary: "#8B5CF6",
    floor: "#F3F6FA",
    mark: "/brand/mark-cyan-violet.svg",
  },
  ember: {
    label: "Coral + Mango",
    accent: "#F97316",
    secondary: "#EC4899",
    floor: "#F7F4F1",
    mark: "/brand/mark-ember.svg",
  },
  indigo: {
    label: "Indigo + Citrus",
    accent: "#4F46E5",
    secondary: "#A3E635",
    floor: "#F4F4FA",
    mark: "/brand/mark-indigo-lime.svg",
  },
};

export const INITIAL_AGENTS: OfficeAgent[] = [
  {
    id: "ceo",
    name: "SINC CEO",
    role: "Founder Interface",
    department: "Command Hub",
    status: "idle",
    currentTask: "No active mission assigned",
    progress: 0,
    color: "#7C3AED",
    model: "Orchestrator",
    position: [0, 0, -4.5],
  },
  {
    id: "team_lead",
    name: "Team Lead",
    role: "Execution Coordinator",
    department: "Command Hub",
    status: "idle",
    currentTask: "Waiting for the next founder request",
    progress: 0,
    color: "#0F9D91",
    model: "Mission Coordinator",
    position: [2.05, 0, -5.15],
  },
  {
    id: "developer",
    name: "Dev Agent",
    role: "Developer",
    department: "Development Studio",
    status: "idle",
    currentTask: "No active mission assigned",
    progress: 0,
    color: "#0EA5E9",
    model: "Code Specialist",
    position: [-6.3, 0, -0.9],
  },
  {
    id: "designer",
    name: "Design Agent",
    role: "Designer",
    department: "Design Studio",
    status: "idle",
    currentTask: "No active mission assigned",
    progress: 0,
    color: "#EC4899",
    model: "Visual Specialist",
    position: [6.3, 0, -0.9],
  },
  {
    id: "researcher",
    name: "Research Agent",
    role: "Researcher",
    department: "Research Library",
    status: "idle",
    currentTask: "No active mission assigned",
    progress: 0,
    color: "#D97706",
    model: "Research Specialist",
    position: [-6.3, 0, 4.25],
  },
  {
    id: "tester",
    name: "QA Agent",
    role: "Tester",
    department: "Quality Lab",
    status: "idle",
    currentTask: "No active mission assigned",
    progress: 0,
    color: "#16A34A",
    model: "Quality Specialist",
    position: [6.3, 0, 4.25],
  },
];

export const STATUS_LABELS: Record<AgentStatus, string> = {
  working: "Working",
  thinking: "Thinking",
  collaborating: "Collaborating",
  idle: "Idle",
  waiting: "Awaiting approval",
  queued: "Mission queued",
  paused: "Paused",
  failed: "Last mission failed",
};
