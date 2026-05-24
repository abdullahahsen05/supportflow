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
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Knowledge Base</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            <span className="font-medium text-indigo-600">{indexedCount}</span> of {docs.length} documents indexed in ChromaDB
          </p>
        </div>
        <button
          type="button"
          onClick={handleReindex}
          disabled={reindexing}
          className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:border-indigo-300 hover:bg-slate-50 hover:text-indigo-700 disabled:opacity-50"
        >
          {reindexing ? "Requesting…" : "Reindex"}
        </button>
      </div>

      {reindexResult && (
        <div className="mb-6 rounded-xl border border-indigo-200 bg-indigo-50 p-4">
          <p className="text-sm font-medium text-indigo-800">{reindexResult.message}</p>
          <code className="mt-2 block rounded-lg bg-indigo-100 px-3 py-2 font-mono text-xs text-indigo-900">
            {reindexResult.cli_command}
          </code>
        </div>
      )}

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
              <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                doc.indexed ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
              }`}>
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
