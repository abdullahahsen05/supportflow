# SupportFlow AI — Session Handoff

> Hand this file to the next Claude Code session. It is the single source of truth for continuing work.

---

## 1. What This Project Is

**SupportFlow AI** — a local-first, production-style agentic customer support platform built as a portfolio project for AI Engineer / GenAI Engineer roles in 2026. It is **not a chatbot**: a LangGraph agent classifies intent, retrieves company docs (RAG), calls business tools over a real PostgreSQL database, validates answers, creates tickets, and escalates to humans.

**Repo root:** `C:\Users\Victus\Desktop\supportflow`

**Full execution plan:** `claude-docs/execution-plan.md`

---

## 2. Hard Constraints (Never Break These)

| Constraint | Detail |
|---|---|
| **Local only, no paid APIs** | Ollama, ChromaDB, PostgreSQL, MLflow, DeepEval, Prometheus, Grafana |
| **No OpenAI / Pinecone / Supabase / Firebase / cloud** | Zero exceptions |
| **No secrets committed** | Only `.env.example` in git; `.env` is gitignored |
| **Docker Postgres on port 5433** | Local Postgres installation occupies 5432; Docker maps `5433:5432`. All DATABASE_URLs use port 5433 |
| **One phase at a time** | Never implement multiple phases without explicit user confirmation |
| **Stop and report after each phase** | Full verification output required before claiming completion |
| **Plans/docs in `claude-docs/`** | All execution plans, session notes, phase notes go there — tracked by git |
| **Superpowers: verification-before-completion** | Must run actual commands and paste live output before any completion claim |

---

## 3. Current Status

### Completed phases

| Phase | Status | Notes |
|---|---|---|
| Phase 0 — Repo scaffolding | ✅ | Folder structure, `.gitignore`, `.env.example`, README, `claude-docs/` |
| Phase 1 — FastAPI backend | ✅ | `GET /health`, pydantic-settings config, CORS, structured logging |
| Phase 2 — PostgreSQL + models + Alembic | ✅ | All 11 tables, single migration, SQLAlchemy 2.0 style |
| Phase 3 — Seed data + KB docs | ✅ | 5 users, 5 orders, 3 subs, 4 payments, 8 KB docs on disk + in DB |
| Phase 4 — ChromaDB ingestion + RAG | ✅ | 8 docs → 29 chunks; retrieval verified; `indexed=True` in DB |
| Phase 5 — Ollama + LangChain chat | ✅ | `POST /api/chat`; RAG → LLM pipeline; 503 on missing model/Ollama down; 13 unit tests passing; live tested with `mistral:7b` |
| Phase 5.5 — Early chat frontend | ✅ | Next.js 15 + React 19 + Tailwind; `/chat` page; suggested questions; source cards; loading/error states; CORS wired; build passes |

### Next up

**Phase 6 — Business tools over Postgres**

Scope: `get_order_status`, `get_user_profile`, `get_subscription_status`, `check_payment_history`, `check_refund_eligibility`, `create_support_ticket`, `escalate_to_human` — all reading/writing Postgres, returning Pydantic results. No LLM deciding to call them yet (that's Phase 7).

---

## 4. Key Technical Decisions

### Database
- **SQLAlchemy 2.0** with `Mapped`/`mapped_column` declarative style
- **String columns for status/role/priority** (not Postgres native ENUM) — simpler migrations
- **No ORM `relationship()`** yet — FK constraints only; relationships added when needed
- **`metadata_json`** instead of `metadata` on `Message` model (SQLAlchemy name collision)
- **`get_or_create()` + `db.flush()`** pattern in seed.py for idempotent FK chaining

### RAG / Embeddings
- **`nomic-embed-text`** via Ollama for embeddings
- **ChromaDB PersistentClient** at `data/chroma/` (gitignored; regenerate with ingest)
- **Stable chunk IDs:** `doc_{doc.id}_chunk_{i}` → `collection.upsert()` for idempotency
- **REPO_ROOT** computed from `__file__` (4 levels up from `backend/app/rag/`) — path-independent
- **Chunk size:** 800, overlap: 100, splitter: `RecursiveCharacterTextSplitter`
- **Collection name:** `supportflow_knowledge_base` (29 chunks across 8 docs)

### Windows / PowerShell
- **`_safe_print()`** in retriever.py: `.encode(encoding, errors="replace")` — prevents cp1252 crashes
- **ASCII-only** for critical output in seed.py (no `✓`, `✗`, `←`)
- **Always run from `backend/`** with `.venv` active for `python -m app.*` commands
- **PowerShell venv activation:** `.venv\Scripts\Activate.ps1`; may need `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

### Config
- All config in `backend/app/core/config.py` (pydantic-settings `Settings` class)
- `.env` loaded from wherever `uvicorn`/`python -m` is run (i.e., `backend/`)
- Key vars: `DATABASE_URL`, `OLLAMA_BASE_URL`, `OLLAMA_CHAT_MODEL`, `OLLAMA_EMBED_MODEL`, `CHROMA_COLLECTION`

---

## 5. Repo Structure (current state)

```
supportflow/
├── .env.example
├── .gitignore
├── README.md
├── docker-compose.yml          ← Postgres 16 on port 5433:5432
├── claude-docs/
│   ├── execution-plan.md
│   ├── phase-2-notes.md
│   ├── phase-3-notes.md
│   └── session-handoff.md      ← this file
├── data/
│   ├── knowledge_base/         ← 8 *.md policy docs
│   └── chroma/                 ← gitignored; 680KB sqlite3 + 3.2MB bin
├── infra/                      ← empty placeholders (Prometheus/Grafana Phase 13)
├── docs/                       ← empty placeholder
├── backend/
│   ├── requirements.txt
│   ├── README.md
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py              ← pulls DATABASE_URL from settings; imports all models
│   │   └── versions/           ← one migration file (all 11 tables)
│   └── app/
│       ├── main.py             ← app factory, CORS, routers
│       ├── core/
│       │   ├── config.py       ← Settings (pydantic-settings)
│       │   └── logging.py      ← structured stdout logging
│       ├── db/
│       │   ├── base.py         ← DeclarativeBase
│       │   ├── session.py      ← engine, SessionLocal, get_db()
│       │   └── seed.py         ← idempotent seed script
│       ├── models/             ← 11 SQLAlchemy models (one file each)
│       │   ├── __init__.py     ← imports all models (needed for Alembic autogenerate)
│       │   ├── user.py
│       │   ├── order.py
│       │   ├── subscription.py
│       │   ├── payment.py
│       │   ├── knowledge_document.py
│       │   ├── conversation.py
│       │   ├── message.py
│       │   ├── tool_call.py
│       │   ├── ticket.py
│       │   ├── feedback.py
│       │   └── eval_result.py
│       ├── api/
│       │   └── health.py       ← GET /health
│       └── rag/
│           ├── __init__.py
│           ├── ingest.py       ← chunk + embed + upsert to Chroma; marks indexed=True
│           └── retriever.py    ← retrieve(query, k) → list[dict]; CLI verification
└── frontend/                   ← placeholder (Next.js added Phase 5.5)
```

---

## 6. Running the Stack

### Prerequisites
- Docker Desktop running
- Ollama running (`ollama serve`), models pulled:
  - `ollama pull nomic-embed-text`
  - `ollama pull mistral:7b` (needed for Phase 5)
- Python venv active

### Start Postgres
```powershell
# from repo root
docker compose up -d postgres
```

### Activate venv + start backend
```powershell
cd backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

### Run seed (Phase 3)
```powershell
# from backend/ with .venv active
python -m app.db.seed
```

### Run RAG ingest (Phase 4)
```powershell
# from backend/ with .venv active
python -m app.rag.ingest
```

### Verify RAG retrieval (Phase 4)
```powershell
python -m app.rag.retriever "refund period"
python -m app.rag.retriever "cancel my subscription"
python -m app.rag.retriever "duplicate charge"
```

### Run Alembic migration
```powershell
# from backend/ with .venv active
alembic upgrade head
```

---

## 7. Seed Data Summary (CloudDesk Inc.)

| Entity | Detail |
|---|---|
| Users | alice@clouddesk.com (admin), bob@clouddesk.com (agent), ayesha@example.com (customer), omar@example.com (customer), sara@example.com (customer) |
| Orders | #1001–1005; **#1004** = Ayesha, shipped, TRK-CD-1004, $149.99 |
| Subscriptions | Ayesha: Pro active; Omar: Starter active; Sara: Pro past_due |
| Payments | **TXN-AYE-001 + TXN-AYE-002** both $79.99 on May 1 + May 3 = duplicate charge demo |
| KB docs | 8 docs in `data/knowledge_base/`, all `indexed=True` after Phase 4 |

---

## 8. Known Issues / Gotchas

| Issue | Status | Notes |
|---|---|---|
| Port 5432 conflict | Permanent | Local Postgres on 5432; Docker always maps to 5433 |
| ChromaDB telemetry warning | Cosmetic | "capture() takes 1 positional argument but 3 were given" — non-blocking |
| Seed user ID gaps | Harmless | First seed run failed → rollback → Postgres sequences advanced; IDs start at 6 not 1; all FKs use queried IDs |
| Windows cp1252 encoding | Fixed | Use `_safe_print()` or ASCII-only output in any new script that prints content |
| `metadata` column name | Fixed | Use `metadata_json` on Message model to avoid SQLAlchemy collision |

---

## 9. Phase 5 Implementation Guide

### Files to create
```
backend/app/llm/__init__.py        ← empty
backend/app/llm/chat.py            ← ChatOllama wrapper + prompt template
backend/app/api/chat.py            ← POST /api/chat router
```

### Wire into main.py
```python
from app.api import chat as chat_router
app.include_router(chat_router.router, prefix="/api")
```

### Request/Response schema
```python
# POST /api/chat
# Request:  { "message": "How do I cancel my subscription?" }
# Response: { "answer": "...", "sources": ["Subscription Policy", ...] }
```

### Key imports available
```python
from langchain_ollama import ChatOllama          # already in requirements.txt
from app.rag.retriever import retrieve           # returns list[dict] with text/title/source
from app.core.config import settings             # OLLAMA_BASE_URL, OLLAMA_CHAT_MODEL
```

### Error handling
- If Ollama is down: catch `httpx.ConnectError` / `Exception` from ChatOllama; return HTTP 503 with `{"detail": "LLM service unavailable. Is Ollama running?"}`
- No crash, no traceback to client

### Prompt template (suggested)
```
You are a helpful customer support agent for CloudDesk Inc.
Use ONLY the context below to answer the question.
If the context does not contain enough information, say so honestly — do not invent details.
Always cite the source document name in your answer.

Context:
{context}

Question: {question}

Answer:
```

### Manual test checklist
1. `ollama pull mistral:7b` (if not already done — ~4GB download)
2. Start backend: `uvicorn app.main:app --reload`
3. Open `http://localhost:8000/docs`
4. POST `/api/chat` with `{"message": "How do I cancel my subscription?"}` → grounded answer + sources
5. POST `/api/chat` with `{"message": "What is 2+2?"}` → honest "I don't know from context" response
6. Stop Ollama → POST `/api/chat` → HTTP 503, no traceback

---

## 10. Phase Sequence Reminder

```
✅ Phase 0  — Repo scaffold
✅ Phase 1  — FastAPI backend
✅ Phase 2  — PostgreSQL + models + Alembic
✅ Phase 3  — Seed data + KB docs
✅ Phase 4  — ChromaDB + RAG retrieval
✅ Phase 5  — Ollama + LangChain minimal chat
✅ Phase 5.5 — Early frontend chat slice (Next.js)
⬜ Phase 6  — Business tools over Postgres  ← NEXT
⬜ Phase 6  — Business tools over Postgres
⬜ Phase 7  — LangGraph agent workflow
⬜ Phase 8  — Persistence + core API endpoints
⬜ Phase 9  — Customer chat frontend
⬜ Phase 10 — Admin dashboard + admin APIs
⬜ Phase 11 — MLflow tracking
⬜ Phase 12 — DeepEval evaluation suite
⬜ Phase 13 — Prometheus metrics + Grafana
⬜ Phase 14 — Full Docker Compose
⬜ Phase 15 — Automated tests (pytest + Playwright)
⬜ Phase 16 — Final polish: README, demo script, UI/UX
```

---

## 11. User Preferences / Workflow

- Always use **Superpowers workflow** (`superpowers:verification-before-completion`) — invoke via `Skill` tool
- Run actual commands; paste live terminal output before claiming any phase complete
- One phase at a time — never jump ahead without explicit confirmation
- Keep responses concise; no verbose commentary
- No emojis unless asked
- No unnecessary comments in code
- Use `claude-docs/` for all phase notes, plans, and handoffs

---

*Last updated: end of Phase 4 session, 2026-05-23*
