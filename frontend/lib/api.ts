import type {
  ChatResponse,
  ConversationDetail,
  ConversationSummary,
  FeedbackRequest,
  FeedbackResponse,
  KnowledgeDocument,
  ReindexResponse,
  Ticket,
  TicketUpdate,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// ── Helper ────────────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const controller = new AbortController();
  // 3-minute timeout — mistral:7b can be slow on CPU hardware
  const timer = setTimeout(() => controller.abort(), 180_000);
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      ...options,
    });
    if (!res.ok) {
      let detail: string;
      try {
        const json = await res.json();
        detail = (json as { detail?: string }).detail ?? `HTTP ${res.status}`;
      } catch {
        detail = `HTTP ${res.status}`;
      }
      throw new Error(detail);
    }
    return res.json() as Promise<T>;
  } finally {
    clearTimeout(timer);
  }
}

// ── Chat ──────────────────────────────────────────────────────────────────────

export async function sendChatMessage(
  message: string,
  k = 4,
  conversationId?: number,
  userEmail?: string
): Promise<ChatResponse> {
  return apiFetch<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({
      message,
      k,
      ...(conversationId != null && { conversation_id: conversationId }),
      ...(userEmail && { user_email: userEmail }),
    }),
  });
}

// ── Feedback ──────────────────────────────────────────────────────────────────

export async function sendFeedback(
  payload: FeedbackRequest
): Promise<FeedbackResponse> {
  return apiFetch<FeedbackResponse>("/api/feedback", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ── Conversations ─────────────────────────────────────────────────────────────

export async function getConversations(
  limit = 20
): Promise<ConversationSummary[]> {
  return apiFetch<ConversationSummary[]>(`/api/conversations?limit=${limit}`);
}

export async function getConversation(id: number): Promise<ConversationDetail> {
  return apiFetch<ConversationDetail>(`/api/conversations/${id}`);
}

// ── Tickets ───────────────────────────────────────────────────────────────────

export async function getTickets(filters?: {
  status?: string;
  priority?: string;
  category?: string;
}): Promise<Ticket[]> {
  const params = new URLSearchParams();
  if (filters?.status) params.set("status", filters.status);
  if (filters?.priority) params.set("priority", filters.priority);
  if (filters?.category) params.set("category", filters.category);
  const qs = params.toString();
  return apiFetch<Ticket[]>(`/api/tickets${qs ? `?${qs}` : ""}`);
}

export async function getTicket(id: number): Promise<Ticket> {
  return apiFetch<Ticket>(`/api/tickets/${id}`);
}

export async function updateTicket(
  id: number,
  payload: TicketUpdate
): Promise<Ticket> {
  return apiFetch<Ticket>(`/api/tickets/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

// ── Knowledge Base ────────────────────────────────────────────────────────────

export async function getKnowledgeBase(): Promise<KnowledgeDocument[]> {
  return apiFetch<KnowledgeDocument[]>("/api/knowledge-base");
}

export async function reindexKnowledgeBase(): Promise<ReindexResponse> {
  return apiFetch<ReindexResponse>("/api/knowledge-base/reindex", {
    method: "POST",
  });
}
