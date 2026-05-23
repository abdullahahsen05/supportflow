# SupportFlow AI Execution Plan

## Context

We are building **SupportFlow AI** from scratch in an empty folder (`C:\Users\Victus\Desktop\supportflow`), on **Windows 11 + PowerShell**. The goal is a portfolio-grade, local-first, production-style agentic customer support platform that proves GenAI + LLMOps + full-stack skills for AI Engineer roles in 2026.

The PRD (`Product Requirements Document.docx`) is the source of truth. This document is a **plan only** — no code is written until you approve. We will then implement **one phase at a time**, stopping after each phase to report and get confirmation.

Constraints reaffirmed: 100% local & free (Ollama, ChromaDB, PostgreSQL, MLflow, DeepEval, Prometheus, Grafana). No OpenAI/Pinecone/Supabase/Firebase/cloud. Simple before advanced. No overengineering. `.env.example` provided, no secrets committed. Use Context7/latest docs for fast-moving libs (LangGraph, LangChain, ChromaDB, FastAPI, MLflow, DeepEval, Next.js).

**Approved adjustments (applied below):**
1. **`docker-compose.yml` lives at repo root** (so `docker compose up --build` runs from root); `infra/` holds only supporting configs (`prometheus.yml`, `grafana/`).
2. **Phase 2 schema stays clean and migration-friendly** — core tables, simple relationships; it is fine to add/adjust tables in later phases. Do not overcomplicate relationships early.
3. **Evaluation starts with deterministic/custom checks** (did the agent call the right tool? include a source? avoid hallucination? create a ticket on escalation?); LLM-as-judge via Ollama added only if it proves reliable.
4. **Embeddings: Ollama `nomic-embed-text` first, with `sentence-transformers/all-MiniLM-L6-v2` as a local fallback** if Ollama embeddings cause issues — so RAG never gets blocked.
5. **New Phase 5.5: a simple frontend chat slice** wired to the basic (pre-LangGraph) chat endpoint, so there's a visible working UI early; it's polished/expanded later.

---

## 1. Understanding of the Product

SupportFlow AI is an **agentic** support platform for a fake SaaS/e-commerce company, not a chatbot. The difference:

- **A basic chatbot** answers FAQ text from a prompt or a single RAG lookup.
- **SupportFlow AI** runs a **LangGraph workflow** that: classifies intent → decides to retrieve docs (RAG), call business tools (orders/subscriptions/payments/refunds over a real Postgres DB), or escalate → validates its own answer (quality check) → creates **tickets** and **escalates to humans** when uncertain/sensitive → stores everything (conversations, messages, tool calls, feedback) → and is **observable** (MLflow runs, Prometheus metrics, Grafana dashboards) and **evaluated** (DeepEval suite).

The standout factors are: local LLM inference, agent orchestration, RAG with source references, tool-calling over real data, human-in-the-loop escalation, ticketing, a feedback loop, evaluation, monitoring, and Dockerized deployment — i.e. AI **product engineering + LLMOps**, not a wrapper.

---

## 2. Recommended Build Strategy

Build in phases because the system has many interdependent subsystems; each must be independently verifiable on a laptop. Principles:

1. **Foundation first, intelligence later.** Stand up the backend, DB, and seed data before any LLM. A broken agent is much easier to debug when the data layer is already trusted.
2. **Prove each external dependency in isolation.** Ollama, ChromaDB, and Postgres each get a dedicated verification phase before being wired into the agent — this isolates the hardest failure points (model speed, Chroma persistence, DB connectivity).
3. **Vertical slice early.** Get a minimal end-to-end chat working (UI → API → LLM → reply) before adding the full LangGraph routing, so you always have a runnable demo.
4. **MVP before V2.** Per PRD §14–15, ship the working agent + ticketing + admin first; layer MLflow/DeepEval/Prometheus/Grafana (LLMOps) after the core works.
5. **Run manually before Docker.** Early phases run via local terminals (uvicorn, npm dev) for fast debugging; full Docker Compose comes near the end, then we verify parity.

Order of features: backend skeleton → Postgres + models + seed → knowledge base docs → ChromaDB/RAG → Ollama/LLM → tools → LangGraph agent → persistence + APIs → chat UI → admin UI → MLflow → DeepEval → Prometheus/Grafana → Docker Compose → tests → README/demo polish.

---

## 3. Phased Implementation Plan

> Each phase ends with a STOP + report (files changed, commands, manual tests, expected result, known issues, ask to continue).

### Phase 0 — Repo scaffolding & docs skeleton
- **Goal:** Create the project skeleton, conventions, and docs shell. Nothing functional yet.
- **Scope:** Folder structure (see §4), root `README.md` skeleton, `.gitignore`, `.env.example`, `backend/` and `frontend/` placeholders, `docs/` folder, `git init`. Remove the temp `_prd_extract.txt`.
- **Out of scope:** Any dependencies, any app code.
- **Files/folders:** `README.md`, `.gitignore`, `.env.example`, `docs/`, `backend/`, `frontend/`, `infra/`, `data/`.
- **Commands:** `git init` (I will tell you exactly).
- **Manual test checklist:** Confirm folder tree matches §4; `.env.example` has no real secrets; `git status` clean-ish.
- **Expected result:** A clean, empty-but-structured repo.
- **Risks/notes:** None. Keep `.gitignore` covering `.env`, `__pycache__`, `node_modules`, `chroma/`, `mlruns/`, `*.db`.

### Phase 1 — Backend foundation (FastAPI)
- **Goal:** Runnable FastAPI app with health check and typed config.
- **Scope:** Python venv, `requirements.txt` (fastapi, uvicorn, pydantic, pydantic-settings), app factory, `GET /health`, settings loaded from `.env`, CORS for the frontend.
- **Out of scope:** DB, LLM, any business logic.
- **Files/folders:** `backend/app/main.py`, `backend/app/core/config.py`, `backend/requirements.txt`, `backend/.env` (local, gitignored).
- **Commands:** create venv, `pip install -r requirements.txt`, `uvicorn app.main:app --reload`.
- **Manual test checklist:** Open `http://localhost:8000/health` → JSON ok; open `http://localhost:8000/docs` → Swagger loads.
- **Expected result:** Backend boots, health endpoint returns 200.
- **Risks/notes:** Windows venv activation (`.venv\Scripts\Activate.ps1`); PowerShell execution policy may need `Set-ExecutionPolicy -Scope Process`.

### Phase 2 — PostgreSQL + SQLAlchemy models + migrations
- **Goal:** Real database with the full schema from PRD §11.
- **Scope:** Run Postgres via the **root `docker-compose.yml`** (Postgres only for now), SQLAlchemy 2.0 models for the core tables (users, conversations, messages, tickets, knowledge_documents, tool_calls, feedback, orders, subscriptions, payments, eval_results), Alembic init + first migration, DB session dependency, enums for status/priority/sender/role. **Keep relationships simple and migration-friendly — it's fine to add/adjust tables in later phases; don't overcomplicate early.**
- **Out of scope:** Seed data, API endpoints.
- **Files/folders:** `docker-compose.yml` (root), `backend/app/db/`, `backend/app/models/`, `backend/alembic/`.
- **Commands:** `docker compose up -d postgres`, `alembic upgrade head`.
- **Manual test checklist:** `docker ps` shows Postgres healthy; `alembic upgrade head` succeeds; connect (psql/DBeaver) and see all tables.
- **Expected result:** All tables created via migration.
- **Risks/notes:** Docker Desktop must be running on Windows; port 5432 conflicts; keep DB URL in `.env`.

### Phase 3 — Seed data + knowledge base documents
- **Goal:** Realistic fake business data and the 8 KB markdown docs.
- **Scope:** Seed script for users/orders (incl. order #1004 from PRD scenarios)/subscriptions/payments; create `data/knowledge_base/*.md` (refund, subscription, shipping, billing, account_setup, troubleshooting, pricing, terms); register `knowledge_documents` rows (indexed=false).
- **Out of scope:** Embeddings/Chroma.
- **Files/folders:** `backend/app/db/seed.py`, `data/knowledge_base/*.md`.
- **Commands:** `python -m app.db.seed`.
- **Manual test checklist:** Query `orders` → #1004 exists with status/tracking; KB files exist with real policy text.
- **Expected result:** DB populated; KB docs on disk.
- **Risks/notes:** Make data internally consistent (a user owns #1004, has a subscription + payments) so tool-calling demos work.

### Phase 4 — ChromaDB ingestion + RAG retrieval
- **Goal:** Persistent local vector store and a retrieval function returning chunks + sources.
- **Scope:** Chunk KB docs (LangChain text splitter), embed with **Ollama `nomic-embed-text`** (fallback: **`sentence-transformers/all-MiniLM-L6-v2`** locally if Ollama embeddings misbehave), persist to local ChromaDB (`data/chroma/`), an `index_documents()` and `retrieve(query, k)` returning text + source filename; mark `knowledge_documents.indexed=true`.
- **Out of scope:** LLM answering, agent.
- **Files/folders:** `backend/app/rag/`, `data/chroma/` (gitignored).
- **Commands:** ensure `ollama pull nomic-embed-text`; `python -m app.rag.ingest`; a small retrieval test script.
- **Manual test checklist:** Run ingest → Chroma persists; query "refund period" → returns chunk from `refund_policy.md` with source.
- **Expected result:** Relevant chunks retrieved with source attribution; persists across restarts.
- **Risks/notes:** **Chroma persistence** — use PersistentClient with a fixed path; embedding dim mismatch if model changes (re-ingest). First `ollama pull` downloads ~270MB.

### Phase 5 — Ollama + LangChain LLM, minimal chat endpoint
- **Goal:** Prove local generation works end-to-end via a simple (non-agentic) `POST /api/chat`.
- **Scope:** LangChain `ChatOllama` wrapper, model `mistral:7b` (configurable), prompt template that injects retrieved RAG context, `POST /api/chat` that retrieves → calls LLM → returns answer + sources. Graceful error if Ollama down.
- **Out of scope:** Intent routing, tools, LangGraph, persistence.
- **Files/folders:** `backend/app/llm/`, `backend/app/api/chat.py`.
- **Commands:** `ollama pull mistral:7b`; call `/api/chat` via Swagger/curl.
- **Manual test checklist:** Ask "How do I cancel my subscription?" → grounded answer + source; stop Ollama → friendly error, no crash.
- **Expected result:** Real RAG answer from local model with source reference.
- **Risks/notes:** **Model speed** on laptop (first token slow, model load) — set sane timeouts, keep prompts short, document expected latency; `mistral:7b` recommended first, `llama3.1:8b` if hardware allows.

### Phase 5.5 — Early frontend chat slice (Next.js)
- **Goal:** A visible, working chat UI wired to the **basic (pre-LangGraph)** `/api/chat` so we can demo in the browser early.
- **Scope:** Minimal Next.js + TS + Tailwind app; single `/chat` page with message list, input box, loading state, and AI answer + sources rendered. Thin API client. No feedback/escalation/ticket UI yet (added in Phase 9).
- **Out of scope:** Admin pages, design polish, feedback buttons, LangGraph features.
- **Files/folders:** `frontend/` (Next app), `frontend/app/chat/`, `frontend/lib/api.ts`.
- **Commands:** `npm install`, `npm run dev`.
- **Manual test checklist:** Browser at `http://localhost:3000/chat` → send "How do I cancel my subscription?" → see grounded answer + source.
- **Expected result:** End-to-end UI → API → Ollama → reply works in the browser.
- **Risks/notes:** CORS (allow `localhost:3000`); API base URL via `NEXT_PUBLIC_*` env. This is intentionally minimal; Phase 9 expands it to the full PRD §12.1 chat page.

### Phase 6 — Business tools over Postgres
- **Goal:** The 7 fake tools from PRD §8.5 as safe, typed functions.
- **Scope:** `get_order_status`, `get_user_profile`, `get_subscription_status`, `check_payment_history`, `check_refund_eligibility`, `create_support_ticket`, `escalate_to_human` — all reading/writing Postgres, returning Pydantic results; handle missing/invalid IDs gracefully.
- **Out of scope:** LLM deciding to call them (that's Phase 7).
- **Files/folders:** `backend/app/tools/`.
- **Commands:** unit-test each tool via a script/pytest.
- **Manual test checklist:** `get_order_status(1004)` → real data; `get_order_status(9999)` → not-found (no hallucination); `check_refund_eligibility` honors policy.
- **Expected result:** All tools return correct structured data and fail safely.
- **Risks/notes:** Keep tools pure & safe (no arbitrary execution); validate inputs.

### Phase 7 — LangGraph agent workflow
- **Goal:** Replace the simple chat with the structured agent (PRD §8.6).
- **Scope:** LangGraph state machine: Input → Intent Classifier → Router → (RAG Retrieval | Tool Selection → Tool Execution) → Response Generation → Quality Check → (Escalation → Ticket Creation) → Final Response. Intent categories per PRD; sentiment detection; confidence score; deterministic routing where possible, LLM only where needed.
- **Out of scope:** Full persistence wiring polish (basic wiring ok), MLflow.
- **Files/folders:** `backend/app/agent/graph.py`, `nodes/`, `state.py`.
- **Commands:** drive via `/api/chat`; scripted runs of the 6 PRD scenarios.
- **Manual test checklist:** Each PRD scenario (FAQ, order #1004, refund, double-charge→ticket+escalate, angry→escalate, unknown→no-hallucinate) behaves as specified.
- **Expected result:** Agent routes correctly, calls tools, creates tickets, escalates.
- **Risks/notes:** LangGraph API churn → use Context7/latest docs; keep classifier prompt strict (JSON intent) to avoid mis-routing; cap loops.

### Phase 8 — Persistence + core API endpoints
- **Goal:** Store conversations/messages/tool_calls/tickets/feedback; expose PRD §13 APIs.
- **Scope:** Persist every turn; endpoints: chat (already), `GET /api/conversations`, `GET /api/conversations/{id}`, `POST /api/feedback`, tickets CRUD (`GET/POST/PATCH`), `GET /api/knowledge-base`, `POST /api/knowledge-base/reindex`.
- **Out of scope:** Admin-specific aggregations (Phase 10), auth.
- **Files/folders:** `backend/app/api/*`, `backend/app/services/`.
- **Commands:** exercise endpoints via Swagger.
- **Manual test checklist:** After a chat, conversation+messages+tool_calls persisted; feedback stored; ticket PATCH updates status.
- **Expected result:** Full conversation lifecycle persisted and queryable.
- **Risks/notes:** Keep service layer thin; consistent Pydantic response schemas.

### Phase 9 — Customer chat frontend (Next.js)
- **Goal:** The `/chat` page (PRD §12.1).
- **Scope:** Next.js + TS + Tailwind app; chat UI, suggested questions, loading/typing state, AI answer with source references, Helpful/Not-helpful/Needs-human/Wrong feedback buttons, escalation button, ticket-status card; API client to backend.
- **Out of scope:** Admin pages, heavy design polish.
- **Files/folders:** `frontend/` (Next app), `app/chat/`, `lib/api.ts`.
- **Commands:** `npm install`, `npm run dev`.
- **Manual test checklist:** In browser, full conversation works; sources show; feedback POSTs; ticket card appears on escalation.
- **Expected result:** Working customer chat against the live backend.
- **Risks/notes:** CORS; API base URL via env; keep functional now, polish in Phase 16 (use UI/UX skill then).

### Phase 10 — Admin dashboard + admin APIs
- **Goal:** `/admin`, `/admin/tickets/[id]`, `/admin/knowledge-base`, `/admin/evaluations` (PRD §12.2–12.5) + `GET /api/admin/*`.
- **Scope:** Stats cards (total conversations, open/escalated tickets, feedback summary), recent conversations, ticket list, ticket detail (history, AI summary, tool calls, sources, status/priority dropdowns), KB page with reindex button, evaluations page (placeholder until Phase 12).
- **Out of scope:** Real auth (PRD MVP excludes); JWT optional later.
- **Files/folders:** `frontend/app/admin/*`, `backend/app/api/admin.py`.
- **Manual test checklist:** Dashboard shows real counts; open a ticket → full detail; update status persists.
- **Expected result:** Admin can review conversations/tickets and update them.
- **Risks/notes:** Keep aggregations simple SQL.

### Phase 11 — MLflow tracking
- **Goal:** Log every AI run (PRD §8.10).
- **Scope:** Local MLflow tracking (file store `mlruns/` or sqlite backend), log model name, prompt version, intent, route, retrieved docs, tool calls, latency, confidence, final response, ticket/escalation flags, feedback.
- **Out of scope:** Model comparison automation (V2 extra).
- **Files/folders:** `backend/app/observability/mlflow_logging.py`.
- **Commands:** `mlflow ui`; do a chat; inspect run.
- **Manual test checklist:** MLflow UI at `:5000` shows a run per interaction with all params/metrics.
- **Expected result:** Each chat creates a tracked MLflow run.
- **Risks/notes:** Don't block the request on logging (fire-and-forget/try-except); MLflow UI port 5000 may clash.

### Phase 12 — DeepEval evaluation suite
- **Goal:** Evaluation tests (PRD §8.11) + `/api/evaluations` + admin page.
- **Scope:** **Start with deterministic/custom checks** (did the agent call `get_order_status` for order questions? create a ticket on billing escalation? include a source for policy answers? avoid hallucination on unknown questions?), persisted to `eval_results`; **then add DeepEval LLM-as-judge (relevance, faithfulness, hallucination) via Ollama only if it proves reliable.** Expose `POST /api/evaluations/run`, `GET /api/evaluations/results`.
- **Out of scope:** RAGAS (optional).
- **Files/folders:** `backend/app/evaluation/`, `backend/tests/eval/`.
- **Commands:** `python -m app.evaluation.run` or pytest; view in admin.
- **Manual test checklist:** Run suite → pass/fail + scores stored and shown on `/admin/evaluations`.
- **Expected result:** Reproducible eval results visible in UI.
- **Risks/notes:** DeepEval may want a judge LLM — point it at Ollama to stay free/local; eval runs can be slow → keep dataset small.

### Phase 13 — Prometheus metrics + Grafana
- **Goal:** Metrics (PRD §8.12) + dashboards.
- **Scope:** `GET /metrics` (prometheus_client) exposing all listed counters/histograms; Prometheus + Grafana via Docker Compose; provisioned Grafana dashboard (requests over time, latency, escalation rate, ticket rate, LLM errors, tool failures, feedback ratio).
- **Out of scope:** Alerting.
- **Files/folders:** `backend/app/observability/metrics.py`, `infra/prometheus.yml`, `infra/grafana/`.
- **Commands:** compose up prometheus+grafana; generate traffic.
- **Manual test checklist:** `/metrics` shows counters incrementing; Prometheus scrapes; Grafana dashboard renders.
- **Expected result:** Live metrics flowing into Grafana.
- **Risks/notes:** **Docker networking** — Prometheus must reach the backend by service name (`host.docker.internal` if backend runs on host); align scrape targets.

### Phase 14 — Full Docker Compose
- **Goal:** One-command local stack.
- **Scope:** Root `docker-compose.yml` expanded to postgres, backend, frontend, chroma (or embedded), mlflow, prometheus, grafana; Dockerfiles for backend & frontend; healthchecks; `.env`-driven; Ollama runs on host (documented) and containers reach it via `host.docker.internal`. Supporting configs stay in `infra/` (`prometheus.yml`, `grafana/`).
- **Out of scope:** Cloud/registry.
- **Files/folders:** `docker-compose.yml` (root, expanded), `backend/Dockerfile`, `frontend/Dockerfile`, `infra/`.
- **Commands:** `docker compose up --build`.
- **Manual test checklist:** Whole demo works from a fresh `compose up`; all services healthy; data persists in volumes.
- **Expected result:** Reproducible full-stack local deployment.
- **Risks/notes:** Ollama-in-Docker is heavy → keep Ollama on host; volume paths for chroma/mlruns/postgres; build context size.

### Phase 15 — Automated tests (pytest + Playwright)
- **Goal:** Confidence + portfolio credibility.
- **Scope:** pytest for tools, RAG retrieval, API endpoints, agent routing (mock LLM where needed); Playwright E2E for the chat flow and admin ticket flow; optional GitHub Actions workflow.
- **Out of scope:** 100% coverage.
- **Files/folders:** `backend/tests/`, `frontend/e2e/`, `.github/workflows/ci.yml`.
- **Commands:** `pytest`; `npx playwright test`.
- **Manual test checklist:** Tests pass locally; E2E drives a real chat.
- **Expected result:** Green test suites.
- **Risks/notes:** Mock/cheap-model the LLM in unit tests to keep CI fast/deterministic.

### Phase 16 — Final polish: README, demo script, UI/UX
- **Goal:** Make it impressive and reproducible.
- **Scope:** Full README (architecture diagram, setup, env, run, screenshots checklist, demo script per PRD §19), polish chat/admin UI **using the UI/UX skill**, capture screenshots (chat, dashboard, MLflow, Grafana, eval).
- **Out of scope:** V3 features.
- **Files/folders:** `README.md`, `docs/`, frontend styles.
- **Manual test checklist:** Follow README from scratch → everything runs; demo script reproducible.
- **Expected result:** Recruiter-ready project.
- **Risks/notes:** Keep README honest about local setup steps (Ollama pulls, Docker).

---

## 4. Suggested Folder Structure

```
supportflow/
├─ README.md
├─ .gitignore
├─ .env.example
├─ docker-compose.yml         # root — `docker compose up --build`
├─ docs/                      # architecture, screenshots, demo script
├─ data/
│  ├─ knowledge_base/         # *.md policy docs
│  └─ chroma/                 # persisted vector store (gitignored)
├─ infra/
│  ├─ prometheus.yml
│  └─ grafana/                # provisioning + dashboards
├─ backend/
│  ├─ requirements.txt
│  ├─ Dockerfile
│  ├─ alembic/
│  └─ app/
│     ├─ main.py
│     ├─ core/                # config, logging
│     ├─ db/                  # session, base, seed
│     ├─ models/              # SQLAlchemy models
│     ├─ schemas/             # Pydantic
│     ├─ api/                 # routers: chat, conversations, tickets, feedback, kb, admin, evaluations
│     ├─ services/            # business logic
│     ├─ rag/                 # chunk, embed, retrieve
│     ├─ llm/                 # Ollama/LangChain wrappers, prompts
│     ├─ tools/               # business tools
│     ├─ agent/               # LangGraph graph, nodes, state
│     ├─ evaluation/          # DeepEval suite
│     └─ observability/       # mlflow + prometheus
│  └─ tests/
└─ frontend/
   ├─ package.json
   ├─ Dockerfile
   └─ app/
      ├─ chat/
      └─ admin/ (tickets/[id], knowledge-base, evaluations)
   └─ e2e/                    # Playwright
```

---

## 5. Database Plan (PRD §11)

| Table | Introduced | Notes |
|---|---|---|
| users | Phase 2 (schema), 3 (seed) | role: customer/agent/admin |
| orders, subscriptions, payments | Phase 2 / 3 | fake business data incl. order #1004 |
| knowledge_documents | Phase 2 / 3 | `indexed` flag flipped in Phase 4 |
| conversations, messages | Phase 2 (schema), 8 (populated) | sender: customer/ai/agent/system |
| tool_calls | Phase 2 / 6–8 | input/output/success/error |
| tickets | Phase 2 / 7–8 | status: open/pending/escalated/resolved/closed; priority: low/medium/high/urgent |
| feedback | Phase 2 / 8 | feedback_type incl. helpful/not_helpful/needs_human/wrong |
| eval_results | Phase 2 / 12 | DeepEval scores |

All schema created up front in Phase 2 via one Alembic migration; tables get populated in the phases above. Alembic used (PRD marks it optional — we include it for production-style credibility).

---

## 6. Agent / RAG Plan (introduction order)

- **PostgreSQL** — Phase 2 (foundation everything else builds on).
- **ChromaDB + embeddings (Ollama `nomic-embed-text`)** — Phase 4; PersistentClient at `data/chroma/`.
- **Ollama + LangChain (`ChatOllama`, `mistral:7b`)** — Phase 5, first in a simple RAG chat to validate the model and retrieval before adding complexity.
- **Tools** — Phase 6, standalone and tested.
- **LangGraph** — Phase 7, ties intent classification + RAG + tools + quality check + escalation + ticketing into one deterministic-where-possible state machine.

Rationale: each dependency is proven alone before the agent orchestrates them, so failures are localized. Model choice: start `mistral:7b`; document upgrade to `llama3.1:8b`.

---

## 7. Testing Plan

- **Manual (every phase):** You run the app in VS Code / browser side-by-side; each phase ships a concrete manual checklist (above).
- **pytest (Phase 6 onward, formalized Phase 15):** unit tests for tools, RAG retrieval, API endpoints, and agent routing with a mocked/cheap LLM for determinism and speed.
- **DeepEval (Phase 12):** LLM-quality evaluation (relevance, faithfulness, hallucination, tool-call/escalation/format correctness) with Ollama as the judge model to stay free; results persisted and surfaced in the admin UI.
- **Playwright (Phase 15):** E2E for the customer chat flow and the admin ticket flow against a running stack.
- **CI (optional, Phase 15):** GitHub Actions running pytest + Playwright with the LLM mocked.

---

## 8. Monitoring & LLMOps Plan

- **MLflow (Phase 11):** local tracking; one run per AI interaction logging params/metrics from PRD §8.10. Non-blocking logging.
- **Prometheus (Phase 13):** backend exposes `/metrics` with all PRD §8.12 counters/histograms; Prometheus scrapes it.
- **Grafana (Phase 13):** provisioned dashboard (requests, latency, escalation rate, ticket rate, LLM errors, tool failures, feedback ratio).
- **Docker Compose (Phase 14):** runs Postgres, backend, frontend, MLflow, Prometheus, Grafana together; Ollama stays on host.

LLMOps comes after the MVP works (PRD V2), so observability instruments a known-good system.

---

## 9. Risk List

| Risk | Mitigation |
|---|---|
| **Ollama model speed** on laptop (slow first token, model load) | Start `mistral:7b`; short prompts; small KB; warm the model; document expected latency; generous timeouts. |
| **First-run model downloads** (mistral ~4GB, nomic ~270MB) | Pull early in Phase 4/5; document in README; verify with `ollama list`. |
| **ChromaDB persistence** (data lost / dim mismatch) | PersistentClient with fixed `data/chroma/` path; re-ingest if embedding model changes; gitignore the store. |
| **Dependency / version churn** (LangGraph, LangChain, ChromaDB APIs change fast) | Pin versions in requirements; use Context7/latest docs at implementation time; isolate LLM/agent code behind thin wrappers. |
| **Docker networking** (Prometheus→backend, containers→Ollama) | Use `host.docker.internal` for host services; service names inside compose; align scrape targets; healthchecks. |
| **Windows/PowerShell friction** (venv activation, ports, line endings) | Provide exact PS commands; `Set-ExecutionPolicy -Scope Process`; document Docker Desktop requirement; `.gitattributes` if needed. |
| **Port conflicts** (5432, 8000, 3000, 5000, 9090, 3001) | Centralize ports in `.env`/compose; document; make configurable. |
| **Agent mis-routing / hallucination** | Strict JSON intent classifier; deterministic routing where possible; quality-check node; no-context → escalate, never invent. |
| **Eval slowness / cost** | Keep eval dataset small; local Ollama judge; run on demand, not per request. |
| **Secrets leakage** | `.env` gitignored from Phase 0; only `.env.example` committed; no keys needed (all local). |
| **Scope creep / overengineering** | Strictly follow phase boundaries; MVP before V2/V3; stop-and-confirm after each phase. |

---

## 10. Immediate Next Step

After you approve this plan, I recommend starting with **Phase 0 — Repo scaffolding & docs skeleton**: create the folder structure from §4, `.gitignore`, `.env.example`, a README skeleton, remove the temp `_prd_extract.txt`, and `git init`. No dependencies installed, no app code yet. Then I stop and report for your confirmation before Phase 1.
