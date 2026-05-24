"use client";

import { useEffect, useRef, useState } from "react";
import { sendChatMessage } from "@/lib/api";
import type { SourceInfo } from "@/lib/types";

const SUGGESTED = [
  "How do I cancel my subscription?",
  "What is your refund period?",
  "Where is my order #1004?",
  "I was charged twice this month.",
  "I want to speak to a human.",
] as const;

interface Message {
  id: string;
  role: "user" | "ai";
  text: string;
  sources?: SourceInfo[];
  isError?: boolean;
}

function SourceCard({ source }: { source: SourceInfo }) {
  return (
    <div className="mt-2 rounded border border-gray-200 bg-white px-3 py-2 text-xs">
      <div className="font-semibold text-gray-800">{source.title}</div>
      <div className="mt-0.5 truncate font-mono text-gray-500">
        {source.file_path}
      </div>
      {source.distance != null && (
        <div className="mt-0.5 text-gray-400">
          distance: {source.distance.toFixed(4)}
        </div>
      )}
    </div>
  );
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
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
      const data = await sendChatMessage(trimmed);
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
          text: `Error: ${msg} — Make sure the backend and Ollama are running.`,
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-screen flex-col bg-gray-50">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white px-6 py-4">
        <h1 className="text-xl font-semibold text-gray-900">SupportFlow AI</h1>
        <p className="text-sm text-gray-500">CloudDesk Customer Support</p>
      </header>

      {/* Message area */}
      <main className="flex-1 overflow-y-auto space-y-4 px-6 py-4">
        {messages.length === 0 && (
          <p className="mt-8 text-center text-sm text-gray-400">
            Ask a question or pick a suggested topic below.
          </p>
        )}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-prose rounded-lg px-4 py-3 text-sm ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : msg.isError
                    ? "border border-red-200 bg-red-50 text-red-700"
                    : "bg-white text-gray-800 shadow-sm"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.text}</p>
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-3 border-t border-gray-100 pt-3">
                  <p className="mb-1 text-xs font-medium text-gray-500">
                    Sources
                  </p>
                  {msg.sources.map((src, i) => (
                    <SourceCard key={i} source={src} />
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="rounded-lg bg-white px-4 py-3 text-sm italic text-gray-400 shadow-sm">
              SupportFlow is thinking…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </main>

      {/* Suggested questions */}
      <div className="border-t border-gray-200 bg-white px-6 pb-2 pt-3">
        <p className="mb-2 text-xs font-medium text-gray-400">
          Suggested questions
        </p>
        <div className="flex flex-wrap gap-2">
          {SUGGESTED.map((q) => (
            <button
              key={q}
              onClick={() => send(q)}
              disabled={loading}
              className="rounded-full border border-gray-300 px-3 py-1 text-xs text-gray-600 transition-opacity hover:bg-gray-50 disabled:opacity-40"
            >
              {q}
            </button>
          ))}
        </div>
        <p className="mb-1 mt-2 text-xs text-gray-400">
          Note: Order lookup, billing tools, ticketing, and human escalation are
          coming in later phases.
        </p>
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 bg-white px-6 py-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
          className="flex gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            placeholder="Type your question…"
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white transition-opacity hover:bg-blue-700 disabled:opacity-50"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
