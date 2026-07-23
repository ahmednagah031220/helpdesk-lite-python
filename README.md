# 🚀 [Tips Hindawi](https://www.tipshindawi.com/) Challenge (June–July) 2026

> 🏆 This repository is my official submission for the [ **Tips Hindawi** ](https://www.tipshindawi.com/) **Challenge (June–July) 2026**.

## 👤 Participant

| Field            | Value                                |
| ---------------- | ------------------------------------ |
| Full Name        | Ahmed Nagah                          |
| Project Name     | HelpDesk Lite (Python)               |
| GitHub Username  | [ahmednagah031220](https://github.com/ahmednagah031220) |
| Challenge Batch  | June–July 2026                       |
| Training Program | Large Language Models (LLMs) Program |
| Organization     | [**Edrak for Ai**](https://edrak4ai.com/en)                         |

---

# 📖 Project Overview

**HelpDesk Lite** is a multi-agent AI help-desk for internal **IT / HR / Facilities** tickets. Agents retrieve evidence from a SQLite ticket history and an internal handbook (PDF + TXT), reason with an LLM (Ollama or offline mock), run a guardrail evaluator, then emit automated artifacts — while a human still approves category and priority before metadata changes.

```
 Ticket ──▶ ORCHESTRATOR
              │
              ├─ Stage 1 RETRIEVAL (parallel)
              │    ├─ retriever_db   (similar SQLite tickets)
              │    └─ retriever_pdf  (handbook PDF/TXT chunks)
              │
              ├─ Stage 2 REASONING (sequential)
              │    triage → knowledge → resolution
              │
              ├─ Stage 3 GUARDRAIL
              │    evaluator (approve / flag)
              │
              └─ Stage 4 AUTOMATED OUTPUTS
                   report.md + email (.eml / SMTP) + webhook (file / HTTP)
                              │
                              ▼
                     Human approve / reject (Support role)
```

---

# ✨ Features

* **Multi-agent pipeline** — parallel retrieval, sequential triage / knowledge / resolution, and a guardrail evaluator
* **Dual knowledge sources** — similar tickets from SQLite + handbook chunks from PDF/TXT
* **Provider auto-fallback** — Ollama when available; deterministic mock so demos and eval always work offline
* **Human-in-the-loop** — Support claims tickets, runs agents, then Approve/Reject metadata (agents never auto-close)
* **Automated fan-out** — markdown brief, local `.eml` (+ optional SMTP), webhook JSON (+ optional HTTP POST)
* **Role-based Streamlit UI** — Employee, Support, and Manager workspaces
* **FastAPI REST API** — tickets, agent runs, decisions, and metrics
* **Golden-set evaluation** — category accuracy and multi-step completion thresholds via `evaluate.py`

---

# 🛠️ Technologies Used

* **Python 3.10+**
* **Streamlit** — interactive demo UI
* **FastAPI + Uvicorn + Pydantic** — REST API
* **SQLite** — tickets and agent-run persistence
* **PyMuPDF / pypdf** — handbook PDF extraction
* **Ollama** (optional) — local LLM chat API (`format=json`)
* **SMTP / HTTP webhooks** — optional notification sinks

---

# ⚙️ Installation

```bash
git clone https://github.com/ahmednagah031220/helpdesk-lite-python.git
cd helpdesk-lite-python

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env        # optional — edit as needed
```

Optional: install and run [Ollama](https://ollama.com/) with a chat model (default `qwen2.5:7b`) for live LLM reasoning. Without Ollama, the app uses the mock provider automatically.

---

# 🚀 Usage

### Streamlit UI

```bash
streamlit run streamlit_app.py
```

1. **Employee** — submit a ticket  
2. **Support** — claim, **Run agents**, review the AI brief + notifications, Approve/Reject  
3. **Manager** — ticket metrics, latency, and AI briefs  

Suggested live ticket: *VPN disconnects every 10 minutes* / *Home office VPN drops after ~10 min.*

### FastAPI

```bash
uvicorn streamlit_app:api --reload --port 8000
# Docs: http://127.0.0.1:8000/docs
```

### Evaluation harness

```bash
python evaluate.py                          # mock (offline, CI-friendly)
EVAL_PROVIDER=ollama python evaluate.py     # live Ollama
```

### Package layout

| Path | Role |
|------|------|
| `helpdesk/` | Core library (retrieval, providers, orchestrator, API, UI) |
| `streamlit_app.py` | Entrypoint — re-exports `api` + launches Streamlit |
| `evaluate.py` | Golden-set accuracy / completion harness |
| `data/` | Internal support handbook (PDF + TXT) |
| `outputs/` | Reports, emails, webhooks, eval JSON |
| `docs/architecture.md` | Pipeline detail |
| `helpdesk_lite.ipynb` | Walkthrough + API TestClient checks |

Environment variables are documented in [`.env.example`](.env.example).

---

# 📸 Demo

**Roles in the Streamlit sidebar:** Employee → Support → Manager.

**Sample AI brief** (`outputs/reports/HD-101.md`):

```markdown
# AI brief — HD-101

**Category:** IT · **Priority:** MEDIUM

## Summary
Relevant handbook guidance was retrieved from the knowledge base.

## Draft reply
Thanks for reporting this. We reviewed similar tickets and the internal handbook...
```

**Mock evaluation snapshot** (`outputs/eval/evaluation-report-mock.json`):

| Metric | Result |
|--------|--------|
| Cases | 12 |
| Valid output rate | 100% |
| Category accuracy | 100% |
| Multi-step completion | 100% |

OpenAPI interactive docs: run the API and visit `/docs`.

---

# 📈 Results

* Modular `helpdesk/` package with clear separation of retrieval, providers, orchestration, API, and UI
* Offline-first design: demos and CI succeed without an LLM via the mock provider
* Golden-set evaluation passes default thresholds (accuracy ≥ 70%, valid/completion ≥ 80%)
* Human gate preserved: agents draft and notify; Support applies category/priority
* Artifact trail under `outputs/` for reports, emails, and webhooks

---

# 🔮 Future Improvements

* Richer retrieval (embeddings / BM25) over handbook and ticket history
* Streaming agent traces in the UI and structured OpenTelemetry spans
* Multi-tenant auth and audit log for approve/reject decisions
* Optional cloud LLM providers behind the same provider interface
* Expanded golden set with priority and draft-quality scoring

---

# 📚 About the Challenge

This project was developed as part of the [**Tips Hindawi**](https://www.tipshindawi.com/) **Challenge (June–July) 2026**.

[Tips Hindawi](https://www.tipshindawi.com/) is the internships department of [**Edrak for Ai**](https://edrak4ai.com/en), and the challenge encourages participants to build real-world projects, apply practical skills, and showcase their work through GitHub.

For more information about the challenge, training programs, and upcoming batches, visit the official [Tips Hindawi](https://www.tipshindawi.com/) website.

---

# 📄 License

This project is shared for educational and portfolio purposes under the [MIT License](LICENSE).
