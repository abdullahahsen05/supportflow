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
    case "closed":    return "bg-slate-100 text-slate-400";
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
        <span className="text-slate-600">Ticket #{ticket.id}</span>
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold text-slate-900">Ticket #{ticket.id}</h1>
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${statusBadge(ticket.status)}`}>
          {ticket.status}
        </span>
        {ticket.category && (
          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs capitalize text-slate-500">
            {ticket.category}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-slate-700">Details</h2>
          <dl className="space-y-4">
            <Field label="Category">{ticket.category}</Field>
            <Field label="Status">{ticket.status}</Field>
            <Field label="Priority">{ticket.priority}</Field>
            <Field label="Summary">
              {ticket.summary ? <p className="whitespace-pre-wrap">{ticket.summary}</p> : null}
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
                <Link href={`/admin/conversations/${ticket.conversation_id}`} className="text-indigo-600 hover:underline">
                  #{ticket.conversation_id}
                </Link>
              </Field>
            )}
          </dl>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-slate-700">Update Ticket</h2>
          <div className="space-y-4">
            <div>
              <label htmlFor="ticket-status" className="mb-1 block text-xs font-medium text-slate-500">Status</label>
              <select
                id="ticket-status"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:border-indigo-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
              >
                {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="ticket-priority" className="mb-1 block text-xs font-medium text-slate-500">Priority</label>
              <select
                id="ticket-priority"
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:border-indigo-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
              >
                {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="ticket-summary" className="mb-1 block text-xs font-medium text-slate-500">Summary</label>
              <textarea
                id="ticket-summary"
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                rows={4}
                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:border-indigo-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
              />
            </div>
            <button
              type="button"
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
