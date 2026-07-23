"""SQLite ticket store and agent-run persistence."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from helpdesk.config import DB_PATH, DEFAULT_TICKETS, OUTPUT_DIR


def db_connect() -> sqlite3.Connection:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT,
            priority TEXT,
            status TEXT NOT NULL,
            submitter TEXT,
            assignee TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_runs (
            ticket_id TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def seed_db_if_empty() -> None:
    with db_connect() as conn:
        count = conn.execute("SELECT COUNT(*) AS n FROM tickets").fetchone()["n"]
        if count:
            return
        for ticket in DEFAULT_TICKETS:
            conn.execute(
                """
                INSERT INTO tickets
                (id, title, description, category, priority, status, submitter, assignee)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticket["id"],
                    ticket["title"],
                    ticket["description"],
                    ticket["category"],
                    ticket["priority"],
                    ticket["status"],
                    ticket["submitter"],
                    ticket["assignee"],
                ),
            )
        conn.commit()


def list_tickets_db() -> list[dict[str, Any]]:
    seed_db_if_empty()
    with db_connect() as conn:
        rows = conn.execute("SELECT * FROM tickets ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


def upsert_ticket_db(ticket: dict[str, Any]) -> None:
    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO tickets
            (id, title, description, category, priority, status, submitter, assignee)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                description=excluded.description,
                category=excluded.category,
                priority=excluded.priority,
                status=excluded.status,
                submitter=excluded.submitter,
                assignee=excluded.assignee
            """,
            (
                ticket["id"],
                ticket["title"],
                ticket["description"],
                ticket.get("category"),
                ticket.get("priority"),
                ticket["status"],
                ticket.get("submitter"),
                ticket.get("assignee"),
            ),
        )
        conn.commit()


def save_run_db(ticket_id: str, result: dict[str, Any]) -> None:
    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO agent_runs (ticket_id, payload, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(ticket_id) DO UPDATE SET
                payload=excluded.payload,
                updated_at=excluded.updated_at
            """,
            (
                ticket_id,
                json.dumps(result),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()


def get_run_db(ticket_id: str) -> dict[str, Any] | None:
    with db_connect() as conn:
        row = conn.execute(
            "SELECT payload FROM agent_runs WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
    return json.loads(row["payload"]) if row else None
