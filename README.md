# SupportFlow AI

> Local-first, production-style **agentic customer support platform** — RAG, tool-calling, human escalation, ticketing, feedback, LLM evaluation, experiment tracking, and monitoring. Runs entirely on your laptop with **no paid APIs**.

SupportFlow AI is a portfolio-grade GenAI / LLMOps project. It is **not a chatbot**: a LangGraph agent classifies intent, retrieves company docs (RAG), calls business tools over a real database, validates its own answers, creates tickets, and escalates to humans when uncertain — all observable and evaluated.

---

## Status

🚧 **Under construction** — built in phases. See the execution plan for the roadmap.

- [x] Phase 0 — Repo scaffolding & docs skeleton
- [ ] Phase 1 — Backend foundation (FastAPI)
- [ ] Phase 2 — PostgreSQL + models + migrations
- [ ] Phase 3 — Seed data + knowledge base docs
- [ ] Phase 4 — ChromaDB ingestion + RAG retrieval
- [ ] Phase 5 — Ollama + LangChain minimal chat
- [ ] Phase 5.5 — Early frontend chat slice
- [ ] Phase 6 — Business tools over Postgres
- [ ] Phase 7 — LangGraph agent workflow
- [ ] Phase 8 — Persistence + core API endpoints
- [ ] Phase 9 — Customer chat frontend
- [ ] Phase 10 — Admin dashboard + admin APIs
- [ ] Phase 11 — MLflow tracking
- [ ] Phase 12 — DeepEval evaluation suite
- [ ] Phase 13 — Prometheus metrics + Grafana
- [ ] Phase 14 — Full Docker Compose
- [ ] Phase 15 — Automated tests (pytest + Playwright)
- [ ] Phase 16 — Final polish: README, demo script, UI/UX

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python, Pydantic, SQLAlchemy |
| Local LLM | Ollama (`mistral:7b`, embeddings `nomic-embed-text`) |
| Agent workflow | LangGraph |
| LLM orchestration | LangChain |
| Vector DB | ChromaDB (local) |
| Main DB | PostgreSQL (local) |
| Tracking | MLflow (local) |
| Evaluation | DeepEval (deterministic checks first) |
| Monitoring | Prometheus + Grafana |
| Testing | Pytest + Playwright |
| Deployment | Docker Compose (local) |

---

## Project Structure

```
supportflow/
├─ docker-compose.yml      # root — `docker compose up --build`
├─ docs/                   # architecture, screenshots, demo script
├─ data/
│  ├─ knowledge_base/      # seeded company policy docs (*.md)
│  └─ chroma/              # persisted vector store (gitignored)
├─ infra/                  # prometheus.yml, grafana/ provisioning
├─ backend/                # FastAPI app, models, agent, rag, tools, evaluation
└─ frontend/               # Next.js customer chat + admin dashboard
```

---

## Getting Started

> Setup instructions are filled in as each phase lands. For now:

```bash
cp .env.example .env
```

Prerequisites (will be needed in later phases): Python 3.12, Node 20+, Docker Desktop, and [Ollama](https://ollama.com).

---

## Documentation

- Architecture, demo script, and screenshots checklist will live in [`docs/`](docs/).
