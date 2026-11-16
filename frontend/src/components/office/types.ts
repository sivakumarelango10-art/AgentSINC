export type AgentStatus =
  | "working"
  | "thinking"
  | "collaborating"
  | "idle"
  | "waiting";

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
};

export const BRAND_THEMES: Record<
  BrandTheme,
  { label: string; accent: string; secondary: string; floor: string; mark: string }
> = {
  cyber: {
    label: "Cyan + Violet",
    accent: "#22D3EE",
    secondary: "#8B5CF6",
    floor: "#14213A",
    mark: "/brand/mark-cyan-violet.svg",
  },
  ember: {
    label: "Ember",
    accent: "#FF7A1A",
    secondary: "#FFC857",
    floor: "#251A17",
    mark: "/brand/mark-ember.svg",
  },
  indigo: {
    label: "Indigo + Lime",
    accent: "#A3E635",
    secondary: "#4F46E5",
    floor: "#1E1B4B",
    mark: "/brand/mark-indigo-lime.svg",
  },
};

export const INITIAL_AGENTS: OfficeAgent[] = [
  {
    id: "ceo",
    name: "SINC CEO",
    role: "Chief Orchestrator",
    department: "Command Hub",
    status: "working",
    currentTask: "Coordinating the company roadmap",
    progress: 72,
    color: "#A78BFA",
    model: "Orchestrator",
    position: [0, 0, -4.5],
  },
  {
    id: "developer",
    name: "Dev Agent",
    role: "Developer",
    department: "Development Studio",
    status: "working",
    currentTask: "Building the AgentSINC foundation",
    progress: 64,
    color: "#22D3EE",
    model: "Code Specialist",
    position: [-6.3, 0, -0.9],
  },
  {
    id: "designer",
    name: "Design Agent",
    role: "Designer",
    department: "Design Studio",
    status: "collaborating",
    currentTask: "Exploring the SINC visual system",
    progress: 48,
    color: "#FB7185",
    model: "Visual Specialist",
    position: [6.3, 0, -0.9],
  },
  {
    id: "researcher",
    name: "Research Agent",
    role: "Researcher",
    department: "Research Library",
    status: "thinking",
    currentTask: "Reviewing architecture options",
    progress: 35,
    color: "#FBBF24",
    model: "Research Specialist",
    position: [-6.3, 0, 4.25],
  },
  {
    id: "tester",
    name: "QA Agent",
    role: "Tester",
    department: "Quality Lab",
    status: "idle",
    currentTask: "Waiting for the next build",
    progress: 0,
    color: "#4ADE80",
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
};
