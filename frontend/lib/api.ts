import type { ChatResponse } from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function chatApi(message: string, k = 4): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, k }),
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

  return res.json() as Promise<ChatResponse>;
}
