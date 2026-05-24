// ── Chat ──────────────────────────────────────────────────────────────────────

export interface ChatRequest {
  message: string;
  k?: number;
  conversation_id?: number;
  user_email?: string;
}

export interface SourceInfo {
  title: string;
  file_path: string;
  chunk_index: number;
  distance: number | null;
}

export interface ChatResponse {
  conversation_id: number;
  answer: string;
  sources: SourceInfo[];
  model: string;
  intent: string | null;
  tool_name: string | null;
  tool_result: Record<string, unknown> | null;
  ticket: Record<string, unknown> | null;
}

// ── Feedback ──────────────────────────────────────────────────────────────────

export type FeedbackType = "helpful" | "not_helpful" | "needs_human" | "wrong_answer";

export interface FeedbackRequest {
  conversation_id: number;
  feedback_type: FeedbackType;
  message_id?: number;
  comment?: string;
}

export interface FeedbackResponse {
  id: number;
  conversation_id: number;
  message_id: number | null;
  feedback_type: FeedbackType;
  comment: string | null;
  created_at: string;
}

// ── Admin — Conversations ─────────────────────────────────────────────────────

export interface ConversationSummary {
  id: number;
  user_id: number | null;
  status: string;
  intent: string | null;
  sentiment: string | null;
  created_at: string;
  updated_at: string;
  latest_message_preview: string | null;
}

export interface AdminMessage {
  id: number;
  sender: string;
  content: string;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
}

export interface TicketBrief {
  id: number;
  status: string;
  priority: string;
  category: string | null;
  summary: string | null;
  created_at: string;
}

export interface ToolCallBrief {
  id: number;
  tool_name: string;
  success: boolean;
  created_at: string;
}

export interface ConversationDetail {
  id: number;
  user_id: number | null;
  status: string;
  intent: string | null;
  sentiment: string | null;
  created_at: string;
  updated_at: string;
  messages: AdminMessage[];
  tickets: TicketBrief[];
  tool_calls: ToolCallBrief[];
}

// ── Admin — Tickets ───────────────────────────────────────────────────────────

export interface Ticket {
  id: number;
  conversation_id: number | null;
  user_id: number | null;
  category: string | null;
  priority: string;
  status: string;
  summary: string | null;
  escalation_reason: string | null;
  assigned_to: number | null;
  created_at: string;
  updated_at: string;
}

export interface TicketUpdate {
  status?: string;
  priority?: string;
  assigned_to?: number;
  summary?: string;
}

// ── Admin — Knowledge Base ────────────────────────────────────────────────────

export interface KnowledgeDocument {
  id: number;
  title: string;
  file_path: string;
  document_type: string | null;
  indexed: boolean;
  created_at: string;
  updated_at: string;
}

export interface ReindexResponse {
  message: string;
  cli_command: string;
}
