"""Streamlit demo UI — Employee / Support / Manager roles."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from helpdesk.config import DB_PATH
from helpdesk.db import (
    db_connect,
    get_run_db,
    list_tickets_db,
    save_run_db,
    seed_db_if_empty,
    upsert_ticket_db,
)
from helpdesk.orchestrator import run_multi_agent, status_metrics
from helpdesk.providers import MockProvider, select_provider
from helpdesk.retrieval import HANDBOOK_CHUNKS


def run_streamlit() -> None:
    import streamlit as st

    st.set_page_config(
        page_title="HelpDesk Lite",
        page_icon="🎫",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    seed_db_if_empty()

    if "tickets" not in st.session_state:
        st.session_state.tickets = list_tickets_db()
    if "runs" not in st.session_state:
        st.session_state.runs = {}

    st.title("HelpDesk Lite")
    st.caption(
        "Multi-agent triage: PDF/DB retrieval → LLM agents → report + email/webhook → "
        "human approve. Eval: `python evaluate.py` · API: `uvicorn streamlit_app:api`"
    )

    with st.sidebar:
        st.markdown("### Demo controls")
        role = st.selectbox("Role", ["Employee", "Support", "Manager"])
        provider_choice = st.selectbox("AI provider", ["auto", "ollama", "mock"])
        st.markdown("---")
        st.markdown(
            f"**Knowledge base:** {len(HANDBOOK_CHUNKS)} chunks  \n"
            f"**DB:** `{DB_PATH.name}`  \n"
            f"**Outputs:** `outputs/`"
        )
        st.markdown(
            "Try: *VPN disconnects every 10 minutes* / "
            "*Home office VPN drops after ~10 min.*"
        )

    def ticket_by_id(ticket_id: str):
        return next((t for t in st.session_state.tickets if t["id"] == ticket_id), None)

    def sync_ticket(ticket: dict[str, Any]) -> None:
        upsert_ticket_db(ticket)
        st.session_state.tickets = list_tickets_db()

    if role == "Employee":
        st.header("Employee workspace")
        submit_tab, tickets_tab = st.tabs(["Submit ticket", "My tickets"])
        with submit_tab:
            with st.form("new-ticket", clear_on_submit=True):
                title = st.text_input("Title")
                description = st.text_area("Description")
                category = st.selectbox("Category", ["IT", "HR", "FACILITIES", "OTHER"])
                submitted = st.form_submit_button("Submit ticket", type="primary")
            if submitted:
                if not title.strip() or not description.strip():
                    st.error("Title and description are required.")
                else:
                    tid = f"HD-{uuid4().hex[:6].upper()}"
                    ticket = {
                        "id": tid,
                        "title": title.strip(),
                        "description": description.strip(),
                        "category": category,
                        "priority": None,
                        "status": "OPEN",
                        "submitter": "Employee Demo",
                        "assignee": None,
                    }
                    sync_ticket(ticket)
                    st.success(f"Created {tid}.")
        with tickets_tab:
            mine = [
                t
                for t in st.session_state.tickets
                if t["submitter"] == "Employee Demo"
            ]
            st.dataframe(mine, use_container_width=True, hide_index=True)

    elif role == "Support":
        st.header("Support workspace")
        queue = [
            t
            for t in st.session_state.tickets
            if t["status"] not in ("RESOLVED", "CLOSED")
            and t["assignee"] in (None, "Support Demo")
        ]
        st.dataframe(queue, use_container_width=True, hide_index=True)
        if not queue:
            st.info("No actionable tickets.")
            st.stop()

        selected_id = st.selectbox("Select ticket", [t["id"] for t in queue])
        ticket = ticket_by_id(selected_id)
        assert ticket is not None

        left, right = st.columns(2)
        with left:
            st.subheader(ticket["title"])
            st.write(ticket["description"])
            st.caption(
                f"{ticket['category']} · {ticket['priority'] or 'No priority'} · "
                f"{ticket['status']}"
            )
            if st.button("Claim ticket", disabled=ticket["assignee"] is not None):
                ticket["assignee"] = "Support Demo"
                sync_ticket(ticket)
                st.rerun()
            next_status = st.selectbox(
                "Human-approved status",
                ["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"],
                index=["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"].index(
                    ticket["status"]
                ),
            )
            if st.button("Apply status"):
                ticket["status"] = next_status
                sync_ticket(ticket)
                st.success("Status updated by support.")

        with right:
            st.subheader("Multi-agent assist")
            if st.button("Run agents", type="primary"):
                try:
                    provider = select_provider(provider_choice)
                    with st.spinner(f"Running via {provider.name}…"):
                        st.session_state.runs[selected_id] = run_multi_agent(
                            ticket, st.session_state.tickets, provider
                        )
                except Exception as error:
                    if provider_choice == "auto":
                        st.warning(f"Ollama failed ({error}); using mock.")
                        st.session_state.runs[selected_id] = run_multi_agent(
                            ticket, st.session_state.tickets, MockProvider()
                        )
                    else:
                        st.error(f"Agent run failed: {error}")

            run = st.session_state.runs.get(selected_id) or get_run_db(selected_id)
            if run:
                st.session_state.runs[selected_id] = run
                st.caption(f"{run['provider']} · {run['durationMs']} ms")
                if run.get("steps"):
                    st.write(
                        " → ".join(
                            f"{s['name']} ({s['durationMs']}ms)" for s in run["steps"]
                        )
                    )
                st.markdown(run.get("report", ""))
                if run.get("reportPath"):
                    st.caption(f"Report file: `{run['reportPath']}`")
                if run.get("notifications"):
                    with st.expander("Automated notifications"):
                        st.json(run["notifications"])
                st.json(
                    {
                        "triage": run["triage"],
                        "knowledge": run["knowledge"],
                        "resolution": run["resolution"],
                        "evaluation": run["evaluation"],
                        "retrieval": run.get("retrieval"),
                    },
                    expanded=False,
                )
                approve, reject = st.columns(2)
                with approve:
                    if st.button(
                        "Approve metadata", disabled=run["decision"] != "PENDING"
                    ):
                        ticket["category"] = run["triage"].get(
                            "category", ticket["category"]
                        )
                        ticket["priority"] = run["triage"].get(
                            "priority", ticket["priority"]
                        )
                        run["decision"] = "APPROVED"
                        sync_ticket(ticket)
                        save_run_db(selected_id, run)
                        st.success("Category/priority applied. Status unchanged.")
                with reject:
                    if st.button("Reject", disabled=run["decision"] != "PENDING"):
                        run["decision"] = "REJECTED"
                        save_run_db(selected_id, run)
                        st.info("Recommendation rejected.")

    else:
        st.header("Manager workspace")
        metrics_map = status_metrics(st.session_state.tickets)
        cols = st.columns(4)
        for col, (status, count) in zip(cols, metrics_map.items()):
            col.metric(status.replace("_", " ").title(), count)

        runs = list(st.session_state.runs.values())
        if not runs:
            with db_connect() as conn:
                rows = conn.execute(
                    "SELECT ticket_id, payload FROM agent_runs"
                ).fetchall()
            for row in rows:
                st.session_state.runs[row["ticket_id"]] = json.loads(row["payload"])
            runs = list(st.session_state.runs.values())

        ok = sum(bool(r.get("evaluation", {}).get("approved")) for r in runs)
        avg = round(sum(r["durationMs"] for r in runs) / len(runs)) if runs else 0
        a, b, c = st.columns(3)
        a.metric("Agent runs", len(runs))
        b.metric("Evaluator approval", f"{ok / len(runs):.0%}" if runs else "—")
        c.metric("Average latency", f"{avg} ms" if runs else "—")

        st.subheader("Team tickets (SQLite)")
        st.dataframe(st.session_state.tickets, use_container_width=True, hide_index=True)
        st.subheader("AI briefs & automated outputs")
        if not runs:
            st.info("Run agents as Support to populate evidence.")
        for tid, run in reversed(list(st.session_state.runs.items())):
            ticket = ticket_by_id(tid)
            with st.expander(f"{tid} — {ticket['title'] if ticket else 'Ticket'}"):
                st.markdown(run.get("report", ""))
                st.json(
                    {
                        "provider": run["provider"],
                        "durationMs": run["durationMs"],
                        "decision": run["decision"],
                        "evaluation": run["evaluation"],
                        "reportPath": run.get("reportPath"),
                        "notifications": run.get("notifications"),
                    }
                )
