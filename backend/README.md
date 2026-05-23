# SupportFlow AI — Backend

FastAPI backend for SupportFlow AI. Currently in Phase 1 (foundation only — no DB, LLM, or agent logic yet).

---

## Quick start

> Run all commands from the `backend/` directory.

### 1. Create and activate a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1   # PowerShell
# or: .venv\Scripts\activate  # Command Prompt
```

> If PowerShell blocks the script, run this first (once per session):
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Create a local `.env` file

```powershell
Copy-Item ..\.env.example .env
```

Edit `.env` as needed (defaults work for local development).

### 4. Start the dev server

```powershell
uvicorn app.main:app --reload
```

Server starts at `http://localhost:8000`.

---

## Endpoints (Phase 1)

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Service health check |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc UI |

### `GET /health` response

```json
{
  "status": "ok",
  "service": "supportflow-api",
  "environment": "development"
}
```

---

## Configuration

All values are loaded from `.env` (or environment variables). See `../.env.example` for the full list. Phase 1 variables:

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `SupportFlow AI` | Application name shown in Swagger |
| `APP_ENV` | `development` | Environment tag returned by `/health` |
| `API_HOST` | `0.0.0.0` | Host to bind |
| `API_PORT` | `8000` | Port to bind |
| `FRONTEND_URL` | `http://localhost:3000` | Primary frontend URL |
| `BACKEND_CORS_ORIGINS` | `http://localhost:3000` | Allowed CORS origins (comma-sep or JSON array) |

---

## Structure

```
backend/
├─ requirements.txt
├─ README.md
└─ app/
   ├─ main.py          # app factory, middleware, routers
   ├─ core/
   │  ├─ config.py     # pydantic-settings, all env vars
   │  └─ logging.py    # structured logging setup
   └─ api/
      └─ health.py     # GET /health
```

More modules (`rag/`, `agent/`, etc.) are added in later phases.

---

## Seed data (Phase 3)

Populates PostgreSQL with CloudDesk fake company data and registers knowledge base documents.

```powershell
# From backend/ with .venv active
python -m app.db.seed
```

The script is **idempotent** — running it multiple times is safe (existing rows are skipped).

### What gets seeded

| Table | Rows | Notable |
|---|---|---|
| `users` | 5 | 3 customers, 1 agent, 1 admin |
| `orders` | 5 | Order #1004 for Ayesha (shipped, TRK-CD-1004) |
| `subscriptions` | 3 | Ayesha: Pro active; Omar: Starter active; Sara: Pro past_due |
| `payments` | 4 | TXN-AYE-001 + TXN-AYE-002 = duplicate charge demo for Ayesha |
| `knowledge_documents` | 8 | All `indexed=false` (indexed by RAG in Phase 4) |

### Knowledge base docs

Located in `../data/knowledge_base/`:
`refund_policy.md`, `subscription_policy.md`, `shipping_policy.md`, `billing_policy.md`,
`account_setup.md`, `troubleshooting.md`, `pricing.md`, `terms.md`

---

## RAG ingestion (Phase 4)

Embeds knowledge base docs into ChromaDB using `nomic-embed-text` via Ollama.

```powershell
# 1. Pull the embedding model (once)
ollama pull nomic-embed-text

# 2. From backend/ with .venv active
python -m app.rag.ingest

# 3. Verify retrieval
python -m app.rag.retriever "refund period"
python -m app.rag.retriever "cancel my subscription"
python -m app.rag.retriever "duplicate charge"
```

- Idempotent: safe to re-run (chunks are upserted with stable IDs).
- ChromaDB persisted to `../data/chroma/` (gitignored; regenerate with ingest).
- Collection name: `supportflow_knowledge_base` (29 chunks across 8 docs).
- If Ollama is not running, the script prints a clear error and exits.
