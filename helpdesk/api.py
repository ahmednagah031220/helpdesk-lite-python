"""FastAPI surface for HelpDesk Lite."""

from __future__ import annotations

import json
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from helpdesk.config import DB_PATH
from helpdesk.db import (
    db_connect,
    get_run_db,
    list_tickets_db,
    save_run_db,
    upsert_ticket_db,
)
from helpdesk.orchestrator import run_multi_agent, status_metrics
from helpdesk.providers import MockProvider, select_provider
from helpdesk.retrieval import HANDBOOK_CHUNKS


def create_app() -> FastAPI:
    app = FastAPI(
        title="HelpDesk Lite",
        description="Multi-agent IT/HR/Facilities help-desk (Python / FastAPI)",
        version="1.1.0",
    )

    class TicketCreate(BaseModel):
        title: str = Field(min_length=1)
        description: str = Field(min_length=1)
        category: Literal["IT", "HR", "FACILITIES", "OTHER"] = "OTHER"
        submitter: str = "Employee Demo"

    class AgentRunRequest(BaseModel):
        provider: Literal["auto", "ollama", "mock"] = "auto"

    class DecisionRequest(BaseModel):
        decision: Literal["APPROVED", "REJECTED"]

    @app.get("/health")
    def health():
        return {
            "ok": True,
            "handbookChunks": len(HANDBOOK_CHUNKS),
            "db": str(DB_PATH),
        }

    @app.get("/tickets")
    def list_tickets():
        return list_tickets_db()

    @app.post("/tickets")
    def create_ticket(body: TicketCreate):
        ticket = {
            "id": f"HD-{uuid4().hex[:6].upper()}",
            "title": body.title.strip(),
            "description": body.description.strip(),
            "category": body.category,
            "priority": None,
            "status": "OPEN",
            "submitter": body.submitter,
            "assignee": None,
        }
        upsert_ticket_db(ticket)
        return ticket

    @app.get("/tickets/{ticket_id}")
    def get_ticket(ticket_id: str):
        ticket = next((t for t in list_tickets_db() if t["id"] == ticket_id), None)
        if not ticket:
            raise HTTPException(404, "Ticket not found")
        return ticket

    @app.post("/tickets/{ticket_id}/agents/run")
    def run_agents(ticket_id: str, body: AgentRunRequest = AgentRunRequest()):
        tickets = list_tickets_db()
        ticket = next((t for t in tickets if t["id"] == ticket_id), None)
        if not ticket:
            raise HTTPException(404, "Ticket not found")
        try:
            provider = select_provider(body.provider)
            result = run_multi_agent(ticket, tickets, provider)
        except Exception as exc:
            if body.provider == "auto":
                result = run_multi_agent(ticket, tickets, MockProvider())
            else:
                raise HTTPException(502, f"Agent run failed: {exc}") from exc
        return result

    @app.get("/tickets/{ticket_id}/agents/run")
    def get_run(ticket_id: str):
        run = get_run_db(ticket_id)
        if not run:
            raise HTTPException(404, "No agent run for this ticket")
        return run

    @app.post("/tickets/{ticket_id}/agents/decision")
    def decide(ticket_id: str, body: DecisionRequest):
        tickets = list_tickets_db()
        ticket = next((t for t in tickets if t["id"] == ticket_id), None)
        run = get_run_db(ticket_id)
        if not ticket or not run:
            raise HTTPException(404, "Ticket or run not found")
        if run["decision"] != "PENDING":
            raise HTTPException(409, f"Already {run['decision']}")
        run["decision"] = body.decision
        if body.decision == "APPROVED":
            ticket["category"] = run["triage"].get("category", ticket["category"])
            ticket["priority"] = run["triage"].get("priority", ticket["priority"])
            upsert_ticket_db(ticket)
        save_run_db(ticket_id, run)
        return {"ticket": ticket, "run": run}

    @app.get("/metrics")
    def metrics():
        tickets = list_tickets_db()
        with db_connect() as conn:
            runs = conn.execute("SELECT payload FROM agent_runs").fetchall()
        pending = sum(
            1 for r in runs if json.loads(r["payload"]).get("decision") == "PENDING"
        )
        return {
            "tickets": status_metrics(tickets),
            "agentRuns": len(runs),
            "pendingDecisions": pending,
            "handbookChunks": len(HANDBOOK_CHUNKS),
        }

    return app


# Module-level app for `uvicorn streamlit_app:api` / `uvicorn helpdesk.api:api`
api = create_app()
