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
  const [messages,       setMessages]       = useState<Message[]>([]);
  const [input,          setInput]          = useState("");
  const [loading,        setLoading]        = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [userEmail,      setUserEmail]      = useState<string>(DEMO_EMAILS[0]);
  const [feedbackGiven,  setFeedbackGiven]  = useState<Set<string>>(new Set());
  const [feedbackMsg,    setFeedbackMsg]    = useState<Record<string, string>>({});
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
    try {
      await sendFeedback({ conversation_id: conversationId, feedback_type: type });
      setFeedbackGiven((prev) => new Set(prev).add(msgId));
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
                type="button"
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
          <label htmlFor="demo-user" className="text-xs text-slate-500">Demo user:</label>
          <select
            id="demo-user"
            value={userEmail}
            onChange={(e) => setUserEmail(e.target.value)}
            disabled={conversationId !== null}
            className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
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

              {/* Feedback row — AI messages only, non-error, after conversation is started */}
              {msg.role === "ai" && !msg.isError && conversationId !== null && (
                <div className="mt-1.5 flex items-center gap-1 px-1">
                  {feedbackMsg[msg.id] ? (
                    <span className="text-xs text-emerald-600">{feedbackMsg[msg.id]}</span>
                  ) : (
                    FEEDBACK_OPTIONS.map(({ type, label }) => (
                      <button
                        type="button"
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
              aria-label="Your message"
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
