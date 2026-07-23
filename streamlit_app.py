"""HelpDesk Lite entrypoint — FastAPI `api` + Streamlit UI.

Run API:       uvicorn streamlit_app:api --reload --port 8000
Run Streamlit: streamlit run streamlit_app.py
Run eval:      python evaluate.py
"""

from __future__ import annotations

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Re-exports keep the notebook and evaluate.py imports stable.
from helpdesk.api import api  # noqa: F401
from helpdesk.config import DEFAULT_TICKETS, DB_PATH, ROOT  # noqa: F401
from helpdesk.db import (  # noqa: F401
    db_connect,
    get_run_db,
    list_tickets_db,
    save_run_db,
    seed_db_if_empty,
    upsert_ticket_db,
)
from helpdesk.orchestrator import run_multi_agent, status_metrics  # noqa: F401
from helpdesk.providers import MockProvider, OllamaProvider, select_provider  # noqa: F401
from helpdesk.retrieval import (  # noqa: F401
    HANDBOOK_CHUNKS,
    normalize_category,
    normalize_priority,
    retrieve_handbook,
    retrieve_similar,
)
from helpdesk.ui import run_streamlit as _run_streamlit

# streamlit run executes this file as __main__; uvicorn imports it as a module.
if __name__ == "__main__":
    _run_streamlit()
