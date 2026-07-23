"""Multi-agent orchestrator: retrieve → reason → guardrail → notify."""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from helpdesk.db import save_run_db
from helpdesk.notifications import notify, write_report_file
from helpdesk.retrieval import (
    normalize_category,
    normalize_priority,
    retrieve_handbook,
    retrieve_similar,
)


def run_multi_agent(
    ticket: dict[str, Any],
    history: list[dict[str, Any]],
    provider: Any,
    *,
    persist: bool = True,
    notify_actions: bool = True,
) -> dict[str, Any]:
    """Orchestrator: parallel retrieval → triage → knowledge → resolution → evaluator → notify."""
    started = time.perf_counter()
    steps: list[dict[str, Any]] = []

    def timed(name: str, fn):
        t0 = time.perf_counter()
        out = fn()
        steps.append(
            {
                "name": name,
                "durationMs": round((time.perf_counter() - t0) * 1000),
            }
        )
        return out

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_similar = pool.submit(retrieve_similar, ticket, history)
        fut_handbook = pool.submit(retrieve_handbook, ticket)
        similar = timed("retriever_db", fut_similar.result)
        handbook = timed("retriever_pdf", fut_handbook.result)

    ticket_text = json.dumps(
        {"title": ticket["title"], "description": ticket["description"]}
    )
    triage = timed(
        "triage",
        lambda: provider.complete(
            "You are a triage agent. Return JSON with category "
            "(IT|HR|FACILITIES|OTHER), priority (LOW|MEDIUM|HIGH|URGENT), "
            "confidence, rationale, tags.",
            f"TRIAGE this ticket: {ticket_text}\nSimilar tickets: {json.dumps(similar)}",
        ),
    )
    triage["category"] = normalize_category(triage.get("category"))
    triage["priority"] = normalize_priority(triage.get("priority"))

    knowledge = timed(
        "knowledge",
        lambda: provider.complete(
            "You are a knowledge agent. Return JSON with relevant, summary, "
            "suggestedSteps, citations.",
            f"Ticket: {ticket_text}\nHandbook evidence: {json.dumps(handbook)}",
        ),
    )
    resolution = timed(
        "resolution",
        lambda: provider.complete(
            "You are a resolution agent. Return JSON with draftResponse, "
            "recommendedActions, needsHumanReview, confidence.",
            f"Ticket: {ticket_text}\nTriage: {json.dumps(triage)}\n"
            f"Knowledge: {json.dumps(knowledge)}",
        ),
    )
    evaluation = timed(
        "evaluator",
        lambda: provider.complete(
            "You are an evaluator agent. Return JSON with approved, confidence, "
            "issues, notes.",
            f"Triage: {json.dumps(triage)}\nKnowledge: {json.dumps(knowledge)}\n"
            f"Resolution: {json.dumps(resolution)}",
        ),
    )

    report = (
        f"# AI brief — {ticket['id']}\n\n"
        f"**Category:** {triage.get('category')} · **Priority:** {triage.get('priority')}\n\n"
        f"## Summary\n{knowledge.get('summary', '')}\n\n"
        f"## Draft reply\n{resolution.get('draftResponse', '')}\n\n"
        f"## Evidence\n"
        f"- Similar tickets: {len(similar)}\n"
        f"- Handbook hits: {len(handbook)} "
        f"({', '.join(sorted({h.get('sourceType', '?') for h in handbook}) or ['none'])})\n"
    )
    report_path = write_report_file(ticket["id"], report) if persist else None

    result: dict[str, Any] = {
        "provider": provider.name,
        "durationMs": round((time.perf_counter() - started) * 1000),
        "steps": steps,
        "retrieval": {"similarTickets": similar, "handbook": handbook},
        "triage": triage,
        "knowledge": knowledge,
        "resolution": resolution,
        "evaluation": evaluation,
        "decision": "PENDING",
        "report": report,
        "reportPath": report_path,
        "notifications": [],
    }

    if notify_actions:
        result["notifications"] = notify(ticket, result)

    if persist:
        save_run_db(ticket["id"], result)

    return result


def status_metrics(tickets: list[dict[str, Any]]) -> dict[str, int]:
    statuses = ("OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED")
    return {s: sum(t["status"] == s for t in tickets) for s in statuses}
