const API_BASE =
  process.env.NEXT_PUBLIC_AGENTSINC_API_URL ?? "http://127.0.0.1:8000";

export type AgentTaskStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export type AgentTask = {
  id: string;
  agent_id: string;
  title: string;
  instructions: string;
  status: AgentTaskStatus;
  progress: number;
  result: string | null;
  error: string | null;
  cancel_requested: boolean;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
};

export type OrchestrationStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export type AgentOrchestration = {
  id: string;
  title: string;
  instructions: string;
  status: OrchestrationStatus;
  stage: "planning" | "executing" | "synthesizing" | "completed" | "failed" | "cancelled";
  plan: { summary: string; tasks: Array<{ agent_id: string; title: string; instructions: string }> } | null;
  result: string | null;
  error: string | null;
  cancel_requested: boolean;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
  progress: number;
  tasks: AgentTask[];
};

export type AgentEvent = {
  id: number;
  agent_id: string;
  task_id: string | null;
  event_type: string;
  message: string;
  created_at: string;
};

export type GenerationMetrics = {
  model: string;
  agent_id: string;
  task_id: string;
  elapsed_seconds: number;
  prompt_tokens: number;
  generated_tokens: number;
  tokens_per_second: number | null;
  load_seconds: number;
  measured_at: string;
};

export type RuntimeStatus = {
  api_connected: boolean;
  worker_online: boolean;
  worker_state: string;
  worker_heartbeat: string | null;
  ollama_online: boolean;
  models: string[];
  selected_model: string | null;
  zero_cost_mode: boolean;
  execution_mode: string;
  last_generation_metrics?: GenerationMetrics;
  memory_records?: number;
  google_search_enabled?: boolean;
};

export type WorkspaceSummary = {
  available: boolean;
  root_name: string;
  file_count: number;
  read_only: boolean;
  sensitive_files_excluded: boolean;
};

export type RuntimeOverview = {
  agents: import("../components/office/types").OfficeAgent[];
  tasks: AgentTask[];
  events: AgentEvent[];
  orchestrations: AgentOrchestration[];
  runtime: RuntimeStatus;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
      cache: "no-store",
    });
  } catch {
    throw new Error("AgentSINC local API is not reachable. Start the backend and worker.");
  }

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message =
      typeof payload.detail === "string" ? payload.detail : `AgentSINC API returned ${response.status}.`;
    throw new Error(message);
  }
  return payload as T;
}

export function getOverview(): Promise<RuntimeOverview> {
  return request<RuntimeOverview>("/api/v1/overview");
}

export function getWorkspaceSummary(): Promise<WorkspaceSummary> {
  return request<WorkspaceSummary>("/api/v1/workspace/summary");
}

export function createMission(input: {
  agent_id: string;
  title: string;
  instructions: string;
}): Promise<{ task: AgentTask }> {
  return request("/api/v1/tasks", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function createOrchestration(input: {
  title: string;
  instructions: string;
}): Promise<{ orchestration: AgentOrchestration }> {
  return request("/api/v1/orchestrations", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function cancelOrchestration(orchestrationId: string): Promise<{ ok: boolean }> {
  return request(`/api/v1/orchestrations/${encodeURIComponent(orchestrationId)}/cancel`, {
    method: "POST",
  });
}

export function controlAgent(
  agentId: string,
  action: "pause" | "resume",
): Promise<{ ok: boolean; paused: boolean; message: string }> {
  return request(`/api/v1/agents/${encodeURIComponent(agentId)}/control`, {
    method: "POST",
    body: JSON.stringify({ action }),
  });
}

export function cancelMission(taskId: string): Promise<{ ok: boolean }> {
  return request(`/api/v1/tasks/${encodeURIComponent(taskId)}/cancel`, {
    method: "POST",
  });
}

export function retryMission(taskId: string): Promise<{ task: AgentTask }> {
  return request(`/api/v1/tasks/${encodeURIComponent(taskId)}/retry`, {
    method: "POST",
  });
}

export function chooseLocalModel(model: string): Promise<{ ok: boolean; selected_model: string }> {
  return request("/api/v1/runtime/model", {
    method: "PATCH",
    body: JSON.stringify({ model }),
  });
}


export type AgentLocation = "desk" | "command" | "discussion" | "meeting";

export function moveAgent(agentId: string, location: AgentLocation): Promise<{
  ok: boolean;
  agent_id: string;
  location: AgentLocation;
}> {
  return request(`/api/v1/agents/${encodeURIComponent(agentId)}/location`, {
    method: "POST",
    body: JSON.stringify({ location }),
  });
}
