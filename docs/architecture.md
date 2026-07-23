# Architecture

## Goal

HelpDesk Lite is a **multi-agent orchestration** demo: retrieve evidence from
multiple sources, process it with an LLM, produce automated artifacts, and keep
a human in the loop.

## Components

| Piece | Role |
|-------|------|
| `helpdesk/` | Package: config, db, retrieval, providers, notifications, orchestrator, api, ui |
| `streamlit_app.py` | Thin entrypoint re-exporting `api` + launching Streamlit |
| `data/` | Knowledge base (`internal-support-handbook.pdf` + `.txt`) |
| `helpdesk.db` | SQLite ticket + agent-run store (created at runtime) |
| `evaluate.py` | Golden-set accuracy / completion harness |
| `outputs/` | Reports, emails, webhooks, eval JSON |
| `helpdesk_lite.ipynb` | Walkthrough + API TestClient checks |

## Pipeline detail

1. **Parallel retrieval** (`ThreadPoolExecutor`)
   - Similar tickets from SQLite (token-overlap ranker)
   - Handbook chunks from PDF/TXT on disk
2. **Sequential LLM agents** (Ollama JSON chat API, or deterministic mock)
   - Triage → Knowledge summary → Resolution draft → Evaluator guardrail
3. **Automated fan-out** (never blocks the main flow on sink failure)
   - Markdown report to disk
   - Email via `.eml` file (+ optional SMTP)
   - Webhook JSON to disk (+ optional HTTP POST)
4. **Human gate** — Support must Approve/Reject category & priority; agents never auto-close tickets

## Provider selection

`select_provider("auto"|"ollama"|"mock")` — auto probes Ollama `/api/tags` and
falls back to mock so demos and CI always work offline.
