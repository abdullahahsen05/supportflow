# Phase 5.5 — Early Customer Chat Frontend

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a minimal Next.js 15 customer chat page at `/chat` that is wired to the existing `POST /api/chat` backend endpoint, with suggested questions, loading state, source cards, and graceful error handling.

**Architecture:** All source lives in `frontend/`. A thin typed API client (`lib/api.ts`) wraps the backend call; types live in `lib/types.ts`. The chat UI is a single client component (`app/chat/page.tsx`). Root `/` redirects to `/chat` via a server component. TypeScript compilation (`npm run type-check`) is the primary correctness gate; `npm run build` is the integration gate.

**Tech Stack:** Next.js 15, React 19, TypeScript 5, Tailwind CSS 3, App Router.

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `frontend/package.json` | Deps, scripts |
| Create | `frontend/tsconfig.json` | TypeScript config |
| Create | `frontend/next.config.ts` | Next.js config |
| Create | `frontend/tailwind.config.ts` | Tailwind content paths |
| Create | `frontend/postcss.config.js` | PostCSS plugins |
| Create | `frontend/app/globals.css` | Tailwind directives |
| Create | `frontend/app/layout.tsx` | Root html/body, metadata |
| Create | `frontend/app/page.tsx` | Root → redirect to /chat |
| Create | `frontend/app/chat/page.tsx` | Full chat UI (client component) |
| Create | `frontend/lib/types.ts` | ChatRequest, ChatResponse, SourceInfo |
| Create | `frontend/lib/api.ts` | chatApi(message, k) → ChatResponse |
| Create | `frontend/.env.local.example` | NEXT_PUBLIC_API_BASE_URL template |
| Create | `frontend/.env.local` | Actual local env (gitignored) |

---

## Task 1: Create `frontend/package.json`

**Files:**
- Create: `frontend/package.json`

- [ ] **Step 1: Create package.json**

```json
{
  "name": "supportflow-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "type-check": "tsc --noEmit"
  },
  "dependencies": {
    "next": "^15.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@types/node": "^22",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.5.3",
    "tailwindcss": "^3.4.17",
    "typescript": "^5.8.3"
  }
}
```

- [ ] **Step 2: Commit**

```powershell
cd C:\Users\Victus\Desktop\supportflow
git add frontend/package.json
git commit -m "feat(phase5.5): add Next.js package.json"
```

---

## Task 2: Create TypeScript and Next.js config files

**Files:**
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.ts`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.js`

- [ ] **Step 1: Create `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 2: Create `frontend/next.config.ts`**

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {};

export default nextConfig;
```

- [ ] **Step 3: Create `frontend/tailwind.config.ts`**

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
export default config;
```

- [ ] **Step 4: Create `frontend/postcss.config.js`**

```javascript
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 5: Commit**

```powershell
git add frontend/tsconfig.json frontend/next.config.ts frontend/tailwind.config.ts frontend/postcss.config.js
git commit -m "feat(phase5.5): add TypeScript, Next.js, and Tailwind config"
```

---

## Task 3: Create app shell (globals.css + layout.tsx)

**Files:**
- Create: `frontend/app/globals.css`
- Create: `frontend/app/layout.tsx`

- [ ] **Step 1: Create `frontend/app/globals.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 2: Create `frontend/app/layout.tsx`**

```typescript
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SupportFlow AI",
  description: "CloudDesk Customer Support",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 3: Commit**

```powershell
git add frontend/app/globals.css frontend/app/layout.tsx
git commit -m "feat(phase5.5): add root layout and Tailwind globals"
```

---

## Task 4: Create `frontend/lib/types.ts` and `frontend/lib/api.ts`

**Files:**
- Create: `frontend/lib/types.ts`
- Create: `frontend/lib/api.ts`

- [ ] **Step 1: Create `frontend/lib/types.ts`**

```typescript
export interface ChatRequest {
  message: string;
  k?: number;
}

export interface SourceInfo {
  title: string;
  file_path: string;
  chunk_index: number;
  distance: number | null;
}

export interface ChatResponse {
  answer: string;
  sources: SourceInfo[];
  model: string;
}
```

- [ ] **Step 2: Create `frontend/lib/api.ts`**

```typescript
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
```

- [ ] **Step 3: Commit**

```powershell
git add frontend/lib/types.ts frontend/lib/api.ts
git commit -m "feat(phase5.5): add API types and chatApi client"
```

---

## Task 5: Create `frontend/app/page.tsx` (root redirect)

**Files:**
- Create: `frontend/app/page.tsx`

- [ ] **Step 1: Create `frontend/app/page.tsx`**

```typescript
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/chat");
}
```

- [ ] **Step 2: Commit**

```powershell
git add frontend/app/page.tsx
git commit -m "feat(phase5.5): redirect root / to /chat"
```

---

## Task 6: Create `frontend/app/chat/page.tsx` (full chat UI)

**Files:**
- Create: `frontend/app/chat/page.tsx`

- [ ] **Step 1: Create `frontend/app/chat/page.tsx`**

```typescript
"use client";

import { useEffect, useRef, useState } from "react";
import { chatApi } from "@/lib/api";
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
      const data = await chatApi(trimmed);
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
      <main className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
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
```

- [ ] **Step 2: Commit**

```powershell
git add frontend/app/chat/page.tsx
git commit -m "feat(phase5.5): add /chat page with message list, suggested questions, source cards"
```

---

## Task 7: Create env files

**Files:**
- Create: `frontend/.env.local.example`
- Create: `frontend/.env.local`

- [ ] **Step 1: Create `frontend/.env.local.example`**

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

- [ ] **Step 2: Create `frontend/.env.local`**

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

- [ ] **Step 3: Verify `.gitignore` already ignores `.env.local`**

Check repo-root `.gitignore` contains `.env.local`. If not, add it.

Expected: `.env.local` is in `.gitignore`.

- [ ] **Step 4: Commit**

```powershell
git add frontend/.env.local.example
git commit -m "feat(phase5.5): add .env.local.example for API base URL"
```

(`.env.local` is gitignored — do not add it.)

---

## Task 8: npm install + verify + run

**Files:** none

- [ ] **Step 1: Install dependencies**

```powershell
cd C:\Users\Victus\Desktop\supportflow\frontend
npm install
```

Expected: `node_modules/` created, no errors. `package-lock.json` created.

- [ ] **Step 2: Run type check**

```powershell
npm run type-check
```

Expected: `0 errors`. If you see errors, they will be in the console — fix before continuing.

- [ ] **Step 3: Run build**

```powershell
npm run build
```

Expected: `✓ Compiled successfully` (or similar green output). Build artifact in `.next/`.

- [ ] **Step 4: Start dev server (backend must also be running)**

```powershell
npm run dev
```

Expected: `▲ Next.js 15.x.x` + `Local: http://localhost:3000`

- [ ] **Step 5: Verify / redirects to /chat**

Open `http://localhost:3000` in browser.
Expected: Browser URL becomes `http://localhost:3000/chat` automatically.

- [ ] **Step 6: Verify /chat loads**

Expected: Page shows "SupportFlow AI" header, empty message area, 5 suggested question chips, input box, Send button.

- [ ] **Step 7: Commit package-lock.json**

```powershell
cd C:\Users\Victus\Desktop\supportflow
git add frontend/package-lock.json
git commit -m "feat(phase5.5): add package-lock.json"
```

---

## Task 9: Update .gitignore for frontend

**Files:**
- Modify: `.gitignore` (repo root)

- [ ] **Step 1: Check what's already in .gitignore**

Open `.gitignore` and verify these entries exist. Add any that are missing:

```
# Frontend
frontend/node_modules/
frontend/.next/
frontend/.env.local
```

- [ ] **Step 2: Commit if changed**

```powershell
git add .gitignore
git commit -m "chore: add frontend node_modules, .next, .env.local to .gitignore"
```

---

## Spec Coverage Self-Review

| Requirement | Covered by |
|-------------|------------|
| Next.js + TS + Tailwind + App Router | Tasks 1–2 |
| `/` redirects to `/chat` | Task 5 |
| `NEXT_PUBLIC_API_BASE_URL` in `.env.local.example` | Task 7 |
| `POST /api/chat` wired via `lib/api.ts` | Task 4 |
| Chat message area (user + AI bubbles) | Task 6 |
| Loading state "SupportFlow is thinking…" | Task 6 |
| Source cards: title, file_path, distance | Task 6 — `SourceCard` |
| 5 suggested question buttons | Task 6 — `SUGGESTED` array |
| Friendly error if backend down | Task 6 — catch block |
| Empty message not submitted | Task 6 — `if (!trimmed)` guard |
| Note about coming features | Task 6 — note paragraph |
| `npm install` + `npm run dev` working | Task 8 |
| `.env.local` gitignored | Task 9 |
| No admin, no tickets, no feedback, no persistence | Nothing added — scope kept minimal |
