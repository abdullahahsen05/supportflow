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
      <div className="mb-7">
        <h1 className="text-xl font-semibold text-slate-900">Operations Dashboard</h1>
        <p className="mt-0.5 text-sm text-slate-500">CloudDesk AI Support · Real-time overview</p>
      </div>

      <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-5">
        <StatCard label="Conversations"   value={conversations.length} borderColor="border-indigo-400" accent="text-indigo-600" />
        <StatCard label="Open Tickets"    value={openTickets}          borderColor="border-emerald-400" accent="text-emerald-600" />
        <StatCard label="Escalated"       value={escalatedTickets}     borderColor="border-red-400"     accent="text-red-600" />
        <StatCard label="Resolved"        value={resolvedTickets}      borderColor="border-slate-300"   accent="text-slate-500" />
        <StatCard label="KB Docs Indexed" value={`${indexedDocs}/${kbDocs.length}`} borderColor="border-amber-400" accent="text-amber-600" />
      </div>

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
