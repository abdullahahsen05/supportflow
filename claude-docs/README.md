# claude-docs

This folder stores all planning documents, architecture decisions, and session context produced during the SupportFlow AI build. It is committed to the repo so any Claude session (or collaborator) can pick up context without needing chat history.

## Contents

| File | Description |
|---|---|
| `execution-plan.md` | Full phased execution plan — source of truth for build order, scope, risks, and DB/agent/testing strategy |
| `phase-2-notes.md` | Port conflict (5432→5433), psycopg3 driver, schema decisions, Alembic setup |
| `phase-3-notes.md` | Seed data design, idempotency pattern, Windows cp1252 Unicode fix |

## Convention

- Add a new file here whenever a significant plan, decision record, or architecture note is produced.
- Keep files up to date as phases complete (e.g., tick off completed phases in `execution-plan.md`).
- Name files descriptively: `execution-plan.md`, `adr-langgraph-state-design.md`, `phase-7-agent-notes.md`, etc.
