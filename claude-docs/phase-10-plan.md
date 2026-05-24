# Phase 10 — Chat Continuity + Feedback + UI/UX Revamp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the customer chat page with multi-turn conversation continuity, per-message feedback buttons, and revamp all frontend pages to a polished AI SaaS aesthetic.

**Architecture:** The chat page gains `conversationId` + `userEmail` state; every `POST /api/chat` sends both; the first response sets `conversationId` for all subsequent turns. Feedback uses `POST /api/feedback` with `conversation_id` + `feedback_type` (no backend changes needed — `message_id` is already optional). All UI files are rewritten with a consistent indigo/slate design system using Tailwind only.

**Tech Stack:** Next.js 15, React 19, TypeScript, Tailwind CSS, existing FastAPI backend at `http://localhost:8000`.

---

## Design System (used across all tasks)

```
bg-slate-50        — page background
bg-white           — surface/card background
border-slate-200   — borders
indigo-600         — primary action colour
indigo-50          — primary tint background
slate-900          — heading text
slate-700          — body text
slate-500          — secondary text
slate-400          — muted/placeholder text
```

Badges:
- escalated: `bg-red-100 text-red-700`
- open:      `bg-emerald-100 text-emerald-700`
- pending:   `bg-amber-100 text-amber-700`
- resolved:  `bg-slate-100 text-slate-500`
- urgent:    `bg-red-100 text-red-700`
- high:      `bg-orange-100 text-orange-700`
- medium:    `bg-amber-100 text-amber-700`
- low:       `bg-sky-100 text-sky-700`

---

## File Map

| File | Action | What changes |
|---|---|---|
| `frontend/lib/types.ts` | Modify | Add `FeedbackRequest`, `FeedbackResponse` |
| `frontend/lib/api.ts` | Modify | Rename `chatApi`→`sendChatMessage`, add `sendFeedback` |
| `frontend/app/chat/page.tsx` | Rewrite | Full UI revamp + continuity + feedback |
| `frontend/app/admin/AdminNav.tsx` | Rewrite | Icons, indigo active state, polished layout |
| `frontend/app/admin/page.tsx` | Rewrite | Stat cards with accents, better tables/badges |
| `frontend/app/admin/tickets/[id]/page.tsx` | Rewrite | Better form layout, indigo primary |
| `frontend/app/admin/knowledge-base/page.tsx` | Rewrite | Better grid cards, badges |
| `frontend/app/admin/conversations/[id]/page.tsx` | Rewrite | Better thread, sidebar cards |

No backend files change. `message_id` is already `Optional[int]` in `FeedbackCreate`.

---

## Task 1: Update `types.ts` and `api.ts`

**Files:**
- Modify: `frontend/lib/types.ts`
- Modify: `frontend/lib/api.ts`

- [ ] **Step 1: Add feedback types to `frontend/lib/types.ts`**

Replace the entire file:

```typescript
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
  feedback_type: string;
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
```

- [ ] **Step 2: Update `frontend/lib/api.ts`**

Replace the entire file:

```typescript
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
```

- [ ] **Step 3: Type-check**

```powershell
cd C:\Users\Victus\Desktop\supportflow\frontend
npx tsc --noEmit
```

Expected: 0 errors (the only breaking change is `chatApi` renamed; nothing else imports it yet).

- [ ] **Step 4: Commit**

```powershell
git add frontend/lib/types.ts frontend/lib/api.ts
git commit -m "feat(phase-10): add FeedbackRequest/Response types, rename chatApi→sendChatMessage, add sendFeedback"
```

---

## Task 2: Rewrite `frontend/app/chat/page.tsx`

**Files:**
- Modify: `frontend/app/chat/page.tsx`

This is the most complex task. Replace the entire file:

- [ ] **Step 1: Replace `frontend/app/chat/page.tsx`**

```tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { sendChatMessage, sendFeedback } from "@/lib/api";
import type { FeedbackType, SourceInfo } from "@/lib/types";

// ── Constants ─────────────────────────────────────────────────────────────────

const DEMO_EMAILS = [
  "ayesha@example.com",
  "omar@example.com",
  "sara@example.com",
] as const;

const SUGGESTED = [
  "Where is my order #1004?",
  "How do I cancel my subscription?",
  "What is your refund period?",
  "I was charged twice this month.",
  "I want to speak to a human.",
] as const;

const FEEDBACK_OPTIONS: { type: FeedbackType; label: string }[] = [
  { type: "helpful",      label: "Helpful" },
  { type: "not_helpful",  label: "Not helpful" },
  { type: "needs_human",  label: "Needs human" },
  { type: "wrong_answer", label: "Wrong answer" },
];

// ── Types ─────────────────────────────────────────────────────────────────────

interface Message {
  id: string;
  role: "user" | "ai";
  text: string;
  sources?: SourceInfo[];
  isError?: boolean;
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SourceCard({ source }: { source: SourceInfo }) {
  return (
    <div className="mt-1.5 flex items-start gap-2 rounded-lg border border-indigo-100 bg-indigo-50/60 px-3 py-2 text-xs">
      <div className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-400" />
      <div className="min-w-0">
        <div className="font-medium text-indigo-900">{source.title}</div>
        <div className="mt-0.5 truncate font-mono text-indigo-500/80">
          {source.file_path}
        </div>
      </div>
    </div>
  );
}

function ThinkingDots() {
  return (
    <div className="flex items-center gap-1 px-1 py-1">
      <span className="h-2 w-2 animate-bounce rounded-full bg-slate-300 [animation-delay:-0.3s]" />
      <span className="h-2 w-2 animate-bounce rounded-full bg-slate-300 [animation-delay:-0.15s]" />
      <span className="h-2 w-2 animate-bounce rounded-full bg-slate-300" />
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ChatPage() {
  const [messages,      setMessages]      = useState<Message[]>([]);
  const [input,         setInput]         = useState("");
  const [loading,       setLoading]       = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [userEmail,     setUserEmail]     = useState<string>(DEMO_EMAILS[0]);
  const [feedbackGiven, setFeedbackGiven] = useState<Set<string>>(new Set());
  const [feedbackMsg,   setFeedbackMsg]   = useState<Record<string, string>>({});
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: "user", text: trimmed },
    ]);
    setInput("");
    setLoading(true);

    try {
      const data = await sendChatMessage(
        trimmed,
        4,
        conversationId ?? undefined,
        userEmail
      );
      if (conversationId === null) setConversationId(data.conversation_id);
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "ai",
          text: data.answer,
          sources: data.sources,
        },
      ]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error.";
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "ai",
          text: `${msg} — Make sure the backend and Ollama are running.`,
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function handleFeedback(msgId: string, type: FeedbackType) {
    if (feedbackGiven.has(msgId) || conversationId === null) return;
    setFeedbackGiven((prev) => new Set(prev).add(msgId));
    try {
      await sendFeedback({ conversation_id: conversationId, feedback_type: type });
      setFeedbackMsg((prev) => ({ ...prev, [msgId]: "Feedback saved" }));
    } catch {
      setFeedbackMsg((prev) => ({ ...prev, [msgId]: "Feedback failed" }));
    }
  }

  function startNewChat() {
    setMessages([]);
    setConversationId(null);
    setFeedbackGiven(new Set());
    setFeedbackMsg({});
  }

  const senderName = userEmail.split("@")[0];

  return (
    <div className="flex h-screen flex-col bg-slate-50">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header className="border-b border-slate-200 bg-white px-6 py-3.5 shadow-sm">
        <div className="mx-auto flex max-w-4xl items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-sm">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </div>
            <div>
              <div className="text-sm font-semibold text-slate-900">SupportFlow AI</div>
              <div className="text-xs text-slate-500">CloudDesk Customer Support</div>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <span className="rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700">
              Local AI · Ollama
            </span>
            {conversationId !== null && (
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                Conversation #{conversationId}
              </span>
            )}
            {messages.length > 0 && (
              <button
                onClick={startNewChat}
                className="text-xs text-slate-400 transition-colors hover:text-slate-600"
              >
                New chat
              </button>
            )}
          </div>
        </div>
      </header>

      {/* ── Session bar ────────────────────────────────────────────────────── */}
      <div className="border-b border-slate-200 bg-white px-6 py-2">
        <div className="mx-auto flex max-w-4xl items-center gap-3">
          <span className="text-xs text-slate-500">Demo user:</span>
          <select
            value={userEmail}
            onChange={(e) => setUserEmail(e.target.value)}
            className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {DEMO_EMAILS.map((email) => (
              <option key={email} value={email}>{email}</option>
            ))}
          </select>
          <span className="ml-auto text-xs text-slate-400">
            Order lookup · Billing · Ticketing · Escalation active
          </span>
        </div>
      </div>

      {/* ── Messages ───────────────────────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto px-6 py-6">
        <div className="mx-auto max-w-4xl space-y-6">

          {/* Empty state */}
          {messages.length === 0 && (
            <div className="mt-12 text-center">
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50">
                <svg className="h-7 w-7 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round"
                    d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
              </div>
              <h2 className="text-base font-semibold text-slate-700">How can I help you today?</h2>
              <p className="mt-1 text-sm text-slate-400">
                Ask about orders, refunds, billing, or subscriptions.
              </p>
            </div>
          )}

          {/* Message list */}
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}
            >
              <div className="mb-1 px-1 text-xs font-medium text-slate-400">
                {msg.role === "user" ? senderName : "SupportFlow AI"}
              </div>
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm shadow-sm ${
                  msg.role === "user"
                    ? "rounded-tr-sm bg-indigo-600 text-white"
                    : msg.isError
                      ? "rounded-tl-sm border border-red-200 bg-red-50 text-red-700"
                      : "rounded-tl-sm border border-slate-200 bg-white text-slate-800"
                }`}
              >
                <p className="whitespace-pre-wrap leading-relaxed">{msg.text}</p>
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-3 border-t border-slate-100 pt-3">
                    <p className="mb-1.5 text-xs font-medium text-slate-500">Sources</p>
                    {msg.sources.map((src, i) => (
                      <SourceCard key={i} source={src} />
                    ))}
                  </div>
                )}
              </div>

              {/* Feedback row (AI messages only, non-error, conversation started) */}
              {msg.role === "ai" && !msg.isError && conversationId !== null && (
                <div className="mt-1.5 flex items-center gap-1 px-1">
                  {feedbackMsg[msg.id] ? (
                    <span className="text-xs text-emerald-600">{feedbackMsg[msg.id]}</span>
                  ) : (
                    FEEDBACK_OPTIONS.map(({ type, label }) => (
                      <button
                        key={type}
                        onClick={() => handleFeedback(msg.id, type)}
                        disabled={feedbackGiven.has(msg.id)}
                        className="rounded-md border border-slate-200 px-2 py-0.5 text-xs text-slate-500 transition-colors hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-600 disabled:cursor-default disabled:opacity-40"
                      >
                        {label}
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>
          ))}

          {/* Loading indicator */}
          {loading && (
            <div className="flex flex-col items-start">
              <div className="mb-1 px-1 text-xs font-medium text-slate-400">SupportFlow AI</div>
              <div className="rounded-2xl rounded-tl-sm border border-slate-200 bg-white px-4 py-3 shadow-sm">
                <ThinkingDots />
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </main>

      {/* ── Suggested questions ─────────────────────────────────────────────── */}
      <div className="border-t border-slate-200 bg-white px-6 py-3">
        <div className="mx-auto max-w-4xl">
          <p className="mb-2 text-xs font-medium text-slate-400">Suggested questions</p>
          <div className="flex flex-wrap gap-2">
            {SUGGESTED.map((q) => (
              <button
                key={q}
                onClick={() => send(q)}
                disabled={loading}
                className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-600 transition-all hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700 disabled:opacity-40"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Input ───────────────────────────────────────────────────────────── */}
      <div className="border-t border-slate-200 bg-white px-6 py-4">
        <div className="mx-auto max-w-4xl">
          <form
            onSubmit={(e) => { e.preventDefault(); send(input); }}
            className="flex gap-2"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
              placeholder="Type your question…"
              className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 disabled:cursor-not-allowed disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-all hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

```powershell
cd C:\Users\Victus\Desktop\supportflow\frontend
npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 3: Commit**

```powershell
git add frontend/app/chat/page.tsx
git commit -m "feat(phase-10): chat continuity, demo user selector, feedback buttons, UI revamp"
```

---

## Task 3: Rewrite `AdminNav.tsx`

**Files:**
- Modify: `frontend/app/admin/AdminNav.tsx`

- [ ] **Step 1: Replace `frontend/app/admin/AdminNav.tsx`**

```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface NavItem {
  href: string;
  label: string;
  exactMatch: boolean;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  {
    href: "/admin",
    label: "Dashboard",
    exactMatch: true,
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
        <path strokeLinecap="round" strokeLinejoin="round"
          d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    ),
  },
  {
    href: "/admin/knowledge-base",
    label: "Knowledge Base",
    exactMatch: false,
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
        <path strokeLinecap="round" strokeLinejoin="round"
          d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
      </svg>
    ),
  },
  {
    href: "/admin",
    label: "Conversations",
    exactMatch: false,
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
        <path strokeLinecap="round" strokeLinejoin="round"
          d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
      </svg>
    ),
  },
];

export default function AdminNav() {
  const path = usePathname();

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-slate-200 bg-white">
      {/* Brand */}
      <div className="border-b border-slate-100 px-5 py-5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600">
            <svg className="h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-900">SupportFlow AI</div>
            <div className="text-xs text-slate-400">Admin Console</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-0.5 px-3 py-4">
        <p className="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
          Operations
        </p>
        {NAV_ITEMS.map(({ href, label, exactMatch, icon }) => {
          const active = label === "Conversations"
            ? path.startsWith("/admin/conversations")
            : exactMatch
              ? path === href
              : path.startsWith(href);
          return (
            <Link
              key={label}
              href={href}
              className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                active
                  ? "bg-indigo-50 text-indigo-700"
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-800"
              }`}
            >
              <span className={active ? "text-indigo-600" : "text-slate-400"}>
                {icon}
              </span>
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-slate-100 px-5 py-4">
        <Link
          href="/chat"
          className="flex items-center gap-2 text-xs text-slate-400 transition-colors hover:text-indigo-600"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Customer Chat
        </Link>
      </div>
    </aside>
  );
}
```

- [ ] **Step 2: Commit**

```powershell
git add frontend/app/admin/AdminNav.tsx
git commit -m "feat(phase-10): polished admin sidebar with icons and indigo active state"
```

---

## Task 4: Rewrite `admin/page.tsx` (Dashboard)

**Files:**
- Modify: `frontend/app/admin/page.tsx`

- [ ] **Step 1: Replace `frontend/app/admin/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getConversations, getKnowledgeBase, getTickets } from "@/lib/api";
import type { ConversationSummary, KnowledgeDocument, Ticket } from "@/lib/types";

// ── Helpers ───────────────────────────────────────────────────────────────────

function statusBadge(status: string): string {
  switch (status) {
    case "escalated": return "bg-red-100 text-red-700";
    case "open":      return "bg-emerald-100 text-emerald-700";
    case "pending":   return "bg-amber-100 text-amber-700";
    case "resolved":  return "bg-slate-100 text-slate-500";
    case "closed":    return "bg-slate-100 text-slate-400";
    default:          return "bg-slate-100 text-slate-500";
  }
}

function priorityBadge(priority: string): string {
  switch (priority) {
    case "urgent": return "bg-red-100 text-red-700";
    case "high":   return "bg-orange-100 text-orange-700";
    case "medium": return "bg-amber-100 text-amber-700";
    case "low":    return "bg-sky-100 text-sky-700";
    default:       return "bg-slate-100 text-slate-500";
  }
}

function Badge({ label, cls }: { label: string; cls: string }) {
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium capitalize ${cls}`}>
      {label}
    </span>
  );
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ── Stat card ─────────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  accent,
  borderColor,
}: {
  label: string;
  value: number | string;
  accent?: string;
  borderColor?: string;
}) {
  return (
    <div className={`rounded-xl border-l-4 bg-white px-5 py-4 shadow-sm ${borderColor ?? "border-slate-200"}`}>
      <div className={`text-2xl font-bold ${accent ?? "text-slate-900"}`}>{value}</div>
      <div className="mt-0.5 text-xs font-medium text-slate-500">{label}</div>
    </div>
  );
}

// ── Section header ────────────────────────────────────────────────────────────

function SectionHeader({ title, count }: { title: string; count?: number }) {
  return (
    <div className="mb-4 flex items-center justify-between">
      <h2 className="text-sm font-semibold text-slate-700">{title}</h2>
      {count !== undefined && (
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
          {count}
        </span>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AdminDashboard() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [tickets,       setTickets]       = useState<Ticket[]>([]);
  const [kbDocs,        setKbDocs]        = useState<KnowledgeDocument[]>([]);
  const [loading,       setLoading]       = useState(true);
  const [error,         setError]         = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getConversations(20), getTickets(), getKnowledgeBase()])
      .then(([convs, tix, docs]) => {
        setConversations(convs);
        setTickets(tix);
        setKbDocs(docs);
      })
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Failed to load data")
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
          <p className="text-sm text-slate-400">Loading dashboard…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="m-8 rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-700">
        <span className="font-medium">Error:</span> {error}
        <span className="ml-2 text-red-500">— Make sure the backend is running on port 8000.</span>
      </div>
    );
  }

  const openTickets      = tickets.filter((t) => t.status === "open").length;
  const escalatedTickets = tickets.filter((t) => t.status === "escalated").length;
  const resolvedTickets  = tickets.filter((t) => t.status === "resolved").length;
  const indexedDocs      = kbDocs.filter((d) => d.indexed).length;

  return (
    <div className="min-h-full bg-slate-50 px-8 py-6">
      {/* Header */}
      <div className="mb-7">
        <h1 className="text-xl font-semibold text-slate-900">Operations Dashboard</h1>
        <p className="mt-0.5 text-sm text-slate-500">CloudDesk AI Support · Real-time overview</p>
      </div>

      {/* Stats */}
      <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-5">
        <StatCard label="Conversations"    value={conversations.length} borderColor="border-indigo-400" accent="text-indigo-600" />
        <StatCard label="Open Tickets"     value={openTickets}          borderColor="border-emerald-400" accent="text-emerald-600" />
        <StatCard label="Escalated"        value={escalatedTickets}     borderColor="border-red-400"     accent="text-red-600" />
        <StatCard label="Resolved"         value={resolvedTickets}      borderColor="border-slate-300"   accent="text-slate-500" />
        <StatCard label="KB Docs Indexed"  value={`${indexedDocs}/${kbDocs.length}`} borderColor="border-amber-400" accent="text-amber-600" />
      </div>

      {/* Recent Conversations */}
      <section className="mb-8">
        <SectionHeader title="Recent Conversations" count={conversations.length} />
        {conversations.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-200 bg-white p-8 text-center">
            <p className="text-sm text-slate-400">
              No conversations yet —{" "}
              <Link href="/chat" className="text-indigo-600 hover:underline">start a chat</Link>.
            </p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/50 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                  <th className="px-4 py-3">ID</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Intent</th>
                  <th className="px-4 py-3">Preview</th>
                  <th className="px-4 py-3">Updated</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {conversations.map((c) => (
                  <tr key={c.id} className="group hover:bg-slate-50/70">
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">#{c.id}</td>
                    <td className="px-4 py-3">
                      <Badge label={c.status} cls={statusBadge(c.status)} />
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-600">
                      {c.intent ?? <span className="text-slate-300">—</span>}
                    </td>
                    <td className="max-w-xs px-4 py-3 text-xs text-slate-500">
                      <span className="block truncate">{c.latest_message_preview ?? "—"}</span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-400">
                      {fmtDate(c.updated_at)}
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        href={`/admin/conversations/${c.id}`}
                        className="text-xs font-medium text-indigo-600 opacity-0 transition-opacity group-hover:opacity-100 hover:underline"
                      >
                        View →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Tickets */}
      <section>
        <SectionHeader title="Support Tickets" count={tickets.length} />
        {tickets.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-200 bg-white p-8 text-center">
            <p className="text-sm text-slate-400">No tickets yet.</p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/50 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                  <th className="px-4 py-3">ID</th>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3">Priority</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Summary</th>
                  <th className="px-4 py-3">Created</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {tickets.map((t) => (
                  <tr key={t.id} className="group hover:bg-slate-50/70">
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">#{t.id}</td>
                    <td className="px-4 py-3 text-xs capitalize text-slate-600">
                      {t.category ?? <span className="text-slate-300">—</span>}
                    </td>
                    <td className="px-4 py-3">
                      <Badge label={t.priority} cls={priorityBadge(t.priority)} />
                    </td>
                    <td className="px-4 py-3">
                      <Badge label={t.status} cls={statusBadge(t.status)} />
                    </td>
                    <td className="max-w-xs px-4 py-3 text-xs text-slate-500">
                      <span className="block truncate">{t.summary ?? "—"}</span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-400">
                      {fmtDate(t.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        href={`/admin/tickets/${t.id}`}
                        className="text-xs font-medium text-indigo-600 opacity-0 transition-opacity group-hover:opacity-100 hover:underline"
                      >
                        Edit →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```powershell
git add frontend/app/admin/page.tsx
git commit -m "feat(phase-10): polished admin dashboard with stat cards, badges, hover rows"
```

---

## Task 5: Rewrite `admin/tickets/[id]/page.tsx`

**Files:**
- Modify: `frontend/app/admin/tickets/[id]/page.tsx`

- [ ] **Step 1: Replace `frontend/app/admin/tickets/[id]/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getTicket, updateTicket } from "@/lib/api";
import type { Ticket } from "@/lib/types";

const STATUSES   = ["open", "pending", "escalated", "resolved", "closed"] as const;
const PRIORITIES = ["low", "medium", "high", "urgent"] as const;

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    month: "short", day: "numeric", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function statusBadge(status: string): string {
  switch (status) {
    case "escalated": return "bg-red-100 text-red-700";
    case "open":      return "bg-emerald-100 text-emerald-700";
    case "pending":   return "bg-amber-100 text-amber-700";
    case "resolved":  return "bg-slate-100 text-slate-500";
    default:          return "bg-slate-100 text-slate-500";
  }
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</dt>
      <dd className="mt-1 text-sm text-slate-800">{children ?? <span className="text-slate-300">—</span>}</dd>
    </div>
  );
}

export default function TicketDetailPage() {
  const params   = useParams();
  const router   = useRouter();
  const ticketId = Number(params.id);

  const [ticket,   setTicket]   = useState<Ticket | null>(null);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState<string | null>(null);
  const [saving,   setSaving]   = useState(false);
  const [saveMsg,  setSaveMsg]  = useState<{ text: string; ok: boolean } | null>(null);

  const [status,   setStatus]   = useState("");
  const [priority, setPriority] = useState("");
  const [summary,  setSummary]  = useState("");

  useEffect(() => {
    getTicket(ticketId)
      .then((t) => {
        setTicket(t);
        setStatus(t.status);
        setPriority(t.priority);
        setSummary(t.summary ?? "");
      })
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Failed to load ticket")
      )
      .finally(() => setLoading(false));
  }, [ticketId]);

  async function handleSave() {
    if (!ticket) return;
    setSaving(true);
    setSaveMsg(null);
    try {
      const updated = await updateTicket(ticketId, {
        status,
        priority,
        summary: summary || undefined,
      });
      setTicket(updated);
      setSaveMsg({ text: "Saved successfully.", ok: true });
    } catch (e: unknown) {
      setSaveMsg({ text: e instanceof Error ? e.message : "Save failed.", ok: false });
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
          <p className="text-sm text-slate-400">Loading ticket…</p>
        </div>
      </div>
    );
  }

  if (error || !ticket) {
    return (
      <div className="m-8 rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-700">
        {error ?? "Ticket not found."}
        <button onClick={() => router.back()} className="ml-3 text-indigo-600 hover:underline">
          Go back
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-full bg-slate-50 px-8 py-6">
      {/* Breadcrumb */}
      <div className="mb-5 flex items-center gap-2 text-xs text-slate-400">
        <Link href="/admin" className="hover:text-indigo-600">Dashboard</Link>
        <span>/</span>
        <span className="text-slate-600">Ticket #{ticket.id}</span>
      </div>

      {/* Title row */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold text-slate-900">Ticket #{ticket.id}</h1>
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${statusBadge(ticket.status)}`}>
          {ticket.status}
        </span>
        {ticket.category && (
          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-500 capitalize">
            {ticket.category}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Details */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-slate-700">Details</h2>
          <dl className="space-y-4">
            <Field label="Category">{ticket.category}</Field>
            <Field label="Status">{ticket.status}</Field>
            <Field label="Priority">{ticket.priority}</Field>
            <Field label="Summary">
              {ticket.summary ? (
                <p className="whitespace-pre-wrap">{ticket.summary}</p>
              ) : null}
            </Field>
            {ticket.escalation_reason && (
              <Field label="Escalation Reason">
                <p className="whitespace-pre-wrap text-orange-700">{ticket.escalation_reason}</p>
              </Field>
            )}
            <Field label="Created">{fmtDate(ticket.created_at)}</Field>
            <Field label="Updated">{fmtDate(ticket.updated_at)}</Field>
            {ticket.conversation_id && (
              <Field label="Conversation">
                <Link
                  href={`/admin/conversations/${ticket.conversation_id}`}
                  className="text-indigo-600 hover:underline"
                >
                  #{ticket.conversation_id}
                </Link>
              </Field>
            )}
          </dl>
        </div>

        {/* Edit form */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-slate-700">Update Ticket</h2>
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">Status</label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:border-indigo-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
              >
                {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">Priority</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:border-indigo-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
              >
                {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">Summary</label>
              <textarea
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                rows={4}
                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:border-indigo-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
              />
            </div>
            <button
              onClick={handleSave}
              disabled={saving}
              className="w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-all hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {saving ? "Saving…" : "Save Changes"}
            </button>
            {saveMsg && (
              <p className={`text-xs ${saveMsg.ok ? "text-emerald-600" : "text-red-600"}`}>
                {saveMsg.text}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```powershell
git add "frontend/app/admin/tickets/[id]/page.tsx"
git commit -m "feat(phase-10): polish ticket detail page with indigo theme"
```

---

## Task 6: Rewrite `admin/knowledge-base/page.tsx`

**Files:**
- Modify: `frontend/app/admin/knowledge-base/page.tsx`

- [ ] **Step 1: Replace `frontend/app/admin/knowledge-base/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { getKnowledgeBase, reindexKnowledgeBase } from "@/lib/api";
import type { KnowledgeDocument, ReindexResponse } from "@/lib/types";

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

export default function KnowledgeBasePage() {
  const [docs,          setDocs]          = useState<KnowledgeDocument[]>([]);
  const [loading,       setLoading]       = useState(true);
  const [error,         setError]         = useState<string | null>(null);
  const [reindexing,    setReindexing]    = useState(false);
  const [reindexResult, setReindexResult] = useState<ReindexResponse | null>(null);

  useEffect(() => {
    getKnowledgeBase()
      .then(setDocs)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Failed to load documents")
      )
      .finally(() => setLoading(false));
  }, []);

  async function handleReindex() {
    setReindexing(true);
    setReindexResult(null);
    try {
      const result = await reindexKnowledgeBase();
      setReindexResult(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Reindex request failed");
    } finally {
      setReindexing(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
          <p className="text-sm text-slate-400">Loading knowledge base…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="m-8 rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-700">
        {error}
      </div>
    );
  }

  const indexedCount = docs.filter((d) => d.indexed).length;

  return (
    <div className="min-h-full bg-slate-50 px-8 py-6">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Knowledge Base</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            <span className="font-medium text-indigo-600">{indexedCount}</span> of {docs.length} documents indexed in ChromaDB
          </p>
        </div>
        <button
          onClick={handleReindex}
          disabled={reindexing}
          className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-50 hover:border-indigo-300 hover:text-indigo-700 disabled:opacity-50"
        >
          {reindexing ? "Requesting…" : "Reindex"}
        </button>
      </div>

      {/* Reindex result */}
      {reindexResult && (
        <div className="mb-6 rounded-xl border border-indigo-200 bg-indigo-50 p-4">
          <p className="text-sm font-medium text-indigo-800">{reindexResult.message}</p>
          <code className="mt-2 block rounded-lg bg-indigo-100 px-3 py-2 font-mono text-xs text-indigo-900">
            {reindexResult.cli_command}
          </code>
        </div>
      )}

      {/* Documents grid */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {docs.map((doc) => (
          <div
            key={doc.id}
            className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-slate-900">{doc.title}</p>
                <p className="mt-0.5 truncate font-mono text-xs text-slate-400">{doc.file_path}</p>
              </div>
              <span
                className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  doc.indexed
                    ? "bg-emerald-100 text-emerald-700"
                    : "bg-slate-100 text-slate-500"
                }`}
              >
                {doc.indexed ? "Indexed" : "Not indexed"}
              </span>
            </div>
            <div className="mt-3 flex items-center gap-4 text-xs text-slate-400">
              {doc.document_type && (
                <span className="rounded-md bg-slate-50 px-2 py-0.5 capitalize text-slate-500">
                  {doc.document_type}
                </span>
              )}
              <span>Updated {fmtDate(doc.updated_at)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```powershell
git add frontend/app/admin/knowledge-base/page.tsx
git commit -m "feat(phase-10): polish knowledge base page"
```

---

## Task 7: Rewrite `admin/conversations/[id]/page.tsx`

**Files:**
- Modify: `frontend/app/admin/conversations/[id]/page.tsx`

- [ ] **Step 1: Replace `frontend/app/admin/conversations/[id]/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getConversation } from "@/lib/api";
import type { ConversationDetail } from "@/lib/types";

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function statusBadge(status: string): string {
  switch (status) {
    case "escalated": return "bg-red-100 text-red-700";
    case "open":      return "bg-emerald-100 text-emerald-700";
    case "pending":   return "bg-amber-100 text-amber-700";
    case "resolved":  return "bg-slate-100 text-slate-500";
    default:          return "bg-slate-100 text-slate-500";
  }
}

export default function ConversationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const convId = Number(params.id);

  const [conv,    setConv]    = useState<ConversationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);

  useEffect(() => {
    getConversation(convId)
      .then(setConv)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Failed to load conversation")
      )
      .finally(() => setLoading(false));
  }, [convId]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
          <p className="text-sm text-slate-400">Loading conversation…</p>
        </div>
      </div>
    );
  }

  if (error || !conv) {
    return (
      <div className="m-8 rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-700">
        {error ?? "Conversation not found."}
        <button onClick={() => router.back()} className="ml-3 text-indigo-600 hover:underline">
          Go back
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-full bg-slate-50 px-8 py-6">
      {/* Breadcrumb */}
      <div className="mb-5 flex items-center gap-2 text-xs text-slate-400">
        <Link href="/admin" className="hover:text-indigo-600">Dashboard</Link>
        <span>/</span>
        <span className="text-slate-600">Conversation #{conv.id}</span>
      </div>

      {/* Meta row */}
      <div className="mb-6 flex flex-wrap items-center gap-2.5">
        <h1 className="text-xl font-semibold text-slate-900">Conversation #{conv.id}</h1>
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${statusBadge(conv.status)}`}>
          {conv.status}
        </span>
        {conv.intent && (
          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-500">
            {conv.intent}
          </span>
        )}
        {conv.sentiment && (
          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-500">
            {conv.sentiment}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Messages — 2/3 */}
        <div className="lg:col-span-2">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">
            Messages ({conv.messages.length})
          </h2>
          {conv.messages.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-200 bg-white p-6 text-center text-sm text-slate-400">
              No messages.
            </div>
          ) : (
            <div className="space-y-4">
              {conv.messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.sender === "customer" ? "justify-end" : "justify-start"}`}
                >
                  <div className="max-w-[80%]">
                    <p className={`mb-1 px-1 text-xs font-medium text-slate-400 ${msg.sender === "customer" ? "text-right" : ""}`}>
                      {msg.sender}
                    </p>
                    <div
                      className={`rounded-2xl px-4 py-3 text-sm shadow-sm ${
                        msg.sender === "customer"
                          ? "rounded-tr-sm bg-indigo-600 text-white"
                          : "rounded-tl-sm border border-slate-200 bg-white text-slate-800"
                      }`}
                    >
                      <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                      <p className={`mt-1.5 text-xs opacity-50`}>{fmtDate(msg.created_at)}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Sidebar — 1/3 */}
        <div className="space-y-5">
          {/* Tickets */}
          <div>
            <h2 className="mb-3 text-sm font-semibold text-slate-700">
              Tickets ({conv.tickets.length})
            </h2>
            {conv.tickets.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-200 bg-white p-4 text-center text-xs text-slate-400">
                No tickets linked.
              </div>
            ) : (
              <div className="space-y-2">
                {conv.tickets.map((t) => (
                  <Link
                    key={t.id}
                    href={`/admin/tickets/${t.id}`}
                    className="block rounded-xl border border-slate-200 bg-white p-3 shadow-sm transition-shadow hover:shadow-md"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs text-slate-400">#{t.id}</span>
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${statusBadge(t.status)}`}>
                        {t.status}
                      </span>
                    </div>
                    {t.summary && (
                      <p className="mt-1 truncate text-xs text-slate-600">{t.summary}</p>
                    )}
                    <p className="mt-1 text-xs text-slate-400">{fmtDate(t.created_at)}</p>
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* Tool calls */}
          {conv.tool_calls.length > 0 && (
            <div>
              <h2 className="mb-3 text-sm font-semibold text-slate-700">
                Tool Calls ({conv.tool_calls.length})
              </h2>
              <div className="space-y-2">
                {conv.tool_calls.map((tc) => (
                  <div
                    key={tc.id}
                    className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs text-slate-700">{tc.tool_name}</span>
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        tc.success ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"
                      }`}>
                        {tc.success ? "ok" : "err"}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-400">{fmtDate(tc.created_at)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```powershell
git add "frontend/app/admin/conversations/[id]/page.tsx"
git commit -m "feat(phase-10): polish conversation detail page"
```

---

## Task 8: Final Verification

- [ ] **Step 1: Type-check**

```powershell
cd C:\Users\Victus\Desktop\supportflow\frontend
npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 2: Production build**

```powershell
npm run build
```

Expected: exit 0, 8 routes compiled, 0 type errors.

- [ ] **Step 3: Backend tests still pass**

```powershell
cd C:\Users\Victus\Desktop\supportflow\backend
.venv\Scripts\python.exe -m pytest tests/ -q
```

Expected: 95 passed.

- [ ] **Step 4: Manual smoke tests**

With backend (`uvicorn app.main:app --reload` from `backend/`) and frontend (`npm run dev` from `frontend/`) running:

1. Open `http://localhost:3000/chat`
   - Confirm header shows "SupportFlow AI · CloudDesk Customer Support"
   - Confirm "Local AI · Ollama" badge visible
   - Confirm demo user selector shows `ayesha@example.com` by default

2. Send "Where is my order #1004?"
   - Expected: answer mentions "shipped" and "TRK-CD-1004"
   - Expected: "Conversation #N" appears in header
   - Expected: Helpful / Not helpful / Needs human / Wrong answer buttons appear under response

3. In same conversation, send "What is your refund period?"
   - Expected: same conversation ID used (check browser Network tab: request body has `conversation_id`)
   - Expected: answer appears in same chat thread

4. Click "Helpful" under an AI message
   - Expected: buttons disappear, "Feedback saved" appears in green

5. Open `http://localhost:3000/admin`
   - Expected: polished dashboard with stat cards, conversations and tickets tables
   - Expected: the two-message conversation from step 2–3 appears as ONE row

6. Click "View →" on that conversation
   - Expected: conversation detail shows both messages in thread

7. Click "Edit →" on a ticket
   - Expected: ticket detail page loads with indigo theme

8. Open `http://localhost:3000/admin/knowledge-base`
   - Expected: 8 docs, Indexed badges in green

9. Send "I was charged twice this month." as ayesha@example.com
   - Expected: duplicate charge flow, escalated ticket created
   - Expected: ticket appears in admin dashboard

---

## Self-Review Checklist

- [x] Part A: `conversationId` stored, sent on every turn — Task 2
- [x] Part A: `userEmail` state with DEMO_EMAILS selector — Task 2
- [x] Part A: "Conversation #N" label in header — Task 2
- [x] Part B: Feedback buttons under each AI response — Task 2
- [x] Part B: `POST /api/feedback` called on click — Task 2
- [x] Part B: "Feedback saved" success state — Task 2
- [x] Part B: Duplicate feedback prevented (feedbackGiven Set) — Task 2
- [x] Part B: `message_id` optional — already optional in backend FeedbackCreate
- [x] Part C: `/chat` revamped — Task 2
- [x] Part C: `/admin` revamped — Tasks 3, 4
- [x] Part C: `/admin/tickets/[id]` revamped — Task 5
- [x] Part C: `/admin/knowledge-base` revamped — Task 6
- [x] Part C: `/admin/conversations/[id]` revamped — Task 7
- [x] No new npm packages
- [x] No backend logic changes
- [x] `chatApi` renamed to `sendChatMessage` everywhere it was used
- [x] "Note: Order lookup…" removed (tools are now active, noted in session bar instead)
