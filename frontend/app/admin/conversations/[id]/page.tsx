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
        <button type="button" onClick={() => router.back()} className="ml-3 text-indigo-600 hover:underline">
          Go back
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-full bg-slate-50 px-8 py-6">
      <div className="mb-5 flex items-center gap-2 text-xs text-slate-400">
        <Link href="/admin" className="hover:text-indigo-600">Dashboard</Link>
        <span>/</span>
        <span className="text-slate-600">Conversation #{conv.id}</span>
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-2.5">
        <h1 className="text-xl font-semibold text-slate-900">Conversation #{conv.id}</h1>
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${statusBadge(conv.status)}`}>
          {conv.status}
        </span>
        {conv.intent && (
          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-500">{conv.intent}</span>
        )}
        {conv.sentiment && (
          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-500">{conv.sentiment}</span>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <h2 className="mb-3 text-sm font-semibold text-slate-700">Messages ({conv.messages.length})</h2>
          {conv.messages.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-200 bg-white p-6 text-center text-sm text-slate-400">
              No messages.
            </div>
          ) : (
            <div className="space-y-4">
              {conv.messages.map((msg) => (
                <div key={msg.id} className={`flex ${msg.sender === "customer" ? "justify-end" : "justify-start"}`}>
                  <div className="max-w-[80%]">
                    <p className={`mb-1 px-1 text-xs font-medium text-slate-400 ${msg.sender === "customer" ? "text-right" : ""}`}>
                      {msg.sender}
                    </p>
                    <div className={`rounded-2xl px-4 py-3 text-sm shadow-sm ${
                      msg.sender === "customer"
                        ? "rounded-tr-sm bg-indigo-600 text-white"
                        : "rounded-tl-sm border border-slate-200 bg-white text-slate-800"
                    }`}>
                      <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                      <p className="mt-1.5 text-xs opacity-50">{fmtDate(msg.created_at)}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-5">
          <div>
            <h2 className="mb-3 text-sm font-semibold text-slate-700">Tickets ({conv.tickets.length})</h2>
            {conv.tickets.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-200 bg-white p-4 text-center text-xs text-slate-400">
                No tickets linked.
              </div>
            ) : (
              <div className="space-y-2">
                {conv.tickets.map((t) => (
                  <Link key={t.id} href={`/admin/tickets/${t.id}`}
                    className="block rounded-xl border border-slate-200 bg-white p-3 shadow-sm transition-shadow hover:shadow-md">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs text-slate-400">#{t.id}</span>
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${statusBadge(t.status)}`}>
                        {t.status}
                      </span>
                    </div>
                    {t.summary && <p className="mt-1 truncate text-xs text-slate-600">{t.summary}</p>}
                    <p className="mt-1 text-xs text-slate-400">{fmtDate(t.created_at)}</p>
                  </Link>
                ))}
              </div>
            )}
          </div>

          {conv.tool_calls.length > 0 && (
            <div>
              <h2 className="mb-3 text-sm font-semibold text-slate-700">Tool Calls ({conv.tool_calls.length})</h2>
              <div className="space-y-2">
                {conv.tool_calls.map((tc) => (
                  <div key={tc.id} className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
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
