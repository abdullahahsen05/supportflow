# Phase 5.5 — Early Customer Chat Frontend: Design Spec

**Date:** 2026-05-23
**Status:** Approved

---

## Goal

A minimal Next.js frontend with a `/chat` page connected to the existing `POST /api/chat` endpoint. Proves the full local stack end-to-end in the browser. No persistence, no tickets, no admin — Phase 5.5 scope only.

---

## Architecture

- **Framework:** Next.js 14, App Router, TypeScript, Tailwind CSS
- **API client:** `frontend/lib/api.ts` — one typed async function, `chatApi(message, k)`, reads `NEXT_PUBLIC_API_BASE_URL` from env
- **Types:** `frontend/lib/types.ts` — `ChatRequest`, `ChatResponse`, `SourceInfo`
- **Pages:**
  - `app/page.tsx` — redirects to `/chat` via `next/navigation` redirect
  - `app/chat/page.tsx` — full chat UI (client component)
  - `app/layout.tsx` — root html/body, Tailwind base styles
- **Env:** `frontend/.env.local.example` with `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`

---

## UI Requirements

### /chat page

1. Header: "SupportFlow AI" + subtitle "CloudDesk Customer Support"
2. Chat message area: scrollable list of user and AI messages
3. User input box + Send button
4. Suggested question chips (5 buttons):
   - "How do I cancel my subscription?"
   - "What is your refund period?"
   - "Where is my order #1004?"
   - "I was charged twice this month."
   - "I want to speak to a human."
5. Loading state: "SupportFlow is thinking..." shown while awaiting response
6. AI message includes source cards below the answer text:
   - `title`, `file_path`, `distance` (if present)
7. Friendly error banner if the API call fails (network error, 503, etc.)
8. Small note in UI: "Order lookup, billing tools, ticketing, and human escalation are coming in later phases."

---

## Data Flow

```
User types / clicks suggested question
  → chatApi(message, k=4)
    → POST NEXT_PUBLIC_API_BASE_URL/api/chat
      → { answer, sources, model }
        → Render AI message + source cards
          (on error: render friendly error banner)
```

---

## Error Handling

- Network error or non-2xx response → show inline error: "Something went wrong. Make sure the backend is running."
- Loading state prevents double-submission (Send button + input disabled while waiting)
- Empty message → do not submit

---

## Constraints (Phase 5.5 only)

- No conversation persistence
- No feedback buttons
- No ticket creation
- No admin pages
- No Docker/Nginx integration
- No auth
- Suggested questions for order/billing/human will return policy-based text answers until Phase 6–7 add tools and LangGraph — noted in UI

---

## Files to create/modify

| File | Action |
|------|--------|
| `frontend/package.json` | Create |
| `frontend/tsconfig.json` | Create |
| `frontend/next.config.ts` | Create |
| `frontend/tailwind.config.ts` | Create |
| `frontend/postcss.config.js` | Create |
| `frontend/.env.local.example` | Create |
| `frontend/app/layout.tsx` | Create |
| `frontend/app/page.tsx` | Create (redirect to /chat) |
| `frontend/app/chat/page.tsx` | Create (full chat UI) |
| `frontend/app/globals.css` | Create (Tailwind directives) |
| `frontend/lib/api.ts` | Create |
| `frontend/lib/types.ts` | Create |
