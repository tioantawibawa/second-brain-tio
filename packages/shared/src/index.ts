/**
 * Shared types, constants, and LLM Cognitive Contracts
 * between Colyseus Backend and Phaser + React Frontend.
 */

export type AgentActionType = "MOVE" | "TALK" | "WORK" | "USE_TOOL" | "HIRE";

export type AgentStatus = "IDLE" | "MOVING" | "THINKING" | "TALKING" | "WORKING" | "HIRING";

export type TaskStatus = "TODO" | "IN_PROGRESS" | "DONE" | "BLOCKED";

export type ToolName =
  | "hire_agent"
  | "vault_search"
  | "vault_write"
  | "execute_code"
  | "web_search";

export interface ToolCallPayload {
  name: ToolName;
  args: Record<string, any>;
}

/**
 * Structured JSON schema required from the LLM during the "Think" phase.
 */
export interface LLMDecisionResponse {
  thought: string;
  action: AgentActionType;
  target: string; // e.g., "320,240" | "WORKSTATION_1" | Agent Name | Task ID
  message?: string; // Spoken dialogue when action === "TALK" or "HIRE"
  toolCall?: ToolCallPayload | string; // Structured tool call or serialized tool invocation
}

export interface HireAgentParams {
  role: string;
  name?: string;
  system_prompt: string;
  specialty?: string;
  spriteKey?: string;
  reason?: string;
}

/**
 * Named Points of Interest (POI) inside the 2D Top-Down RPG Virtual Office (in pixels).
 * Tile size = 32x32, Map = 30x20 tiles (960x640 px).
 */
export const OFFICE_ZONES: Record<string, { x: number; y: number; label: string }> = {
  SPAWN_DOOR: { x: 480, y: 580, label: "Pintu Masuk Kantor" },
  TASK_BOARD: { x: 480, y: 120, label: "Papan Tugas Utama (Kanban)" },
  MEETING_TABLE: { x: 480, y: 320, label: "Meja Diskusi & War Room" },
  WORKSTATION_PM: { x: 200, y: 200, label: "Meja Product Manager" },
  WORKSTATION_ENG: { x: 200, y: 360, label: "Meja Software Engineer" },
  WORKSTATION_DATA: { x: 760, y: 200, label: "Meja Data & AI Analyst" },
  WORKSTATION_RESEARCH: { x: 760, y: 360, label: "Lab Riset & Web Search" },
  VAULT_LIBRARY: { x: 160, y: 520, label: "Rak Arsip Second Brain Vault" },
  RECRUITMENT_POD: { x: 800, y: 520, label: "Pod Rekrutmen Agen Baru (HR Portal)" },
  COFFEE_CORNER: { x: 820, y: 120, label: "Sudut Kopi & Istirahat" },
};

export const PERCEPTION_RADIUS_PX = 220; // Radius in pixels for nearby agent & chat perception
export const COGNITIVE_TICK_MS = 15000;  // 15 seconds Perceive-Think-Act cycle
export const MOVEMENT_TICK_MS = 50;      // 20 ticks/sec smooth coordinate interpolation
export const AGENT_SPEED_PX_PER_SEC = 110;
