"""Automated outputs — markdown report, email sink, webhook."""

from __future__ import annotations

import json
import os
import smtplib
import time
from email.message import EmailMessage
from typing import Any

from helpdesk.config import EMAIL_DIR, REPORT_DIR, WEBHOOK_DIR


def write_report_file(ticket_id: str, report_md: str) -> str:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"{ticket_id}.md"
    path.write_text(report_md, encoding="utf-8")
    return str(path)


def send_email_notification(ticket: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """SMTP if configured; otherwise persist a local .eml under outputs/emails/."""
    EMAIL_DIR.mkdir(parents=True, exist_ok=True)
    subject = f"[HelpDesk] AI brief ready — {ticket['id']}: {ticket['title']}"
    body = (
        f"Ticket: {ticket['id']}\n"
        f"Title: {ticket['title']}\n"
        f"Provider: {result.get('provider')}\n"
        f"Decision: {result.get('decision')}\n\n"
        f"{result.get('report', '')}\n"
    )
    msg = EmailMessage()
    to_addr = os.getenv("NOTIFY_EMAIL_TO", "support@helpdesk.local")
    from_addr = os.getenv("NOTIFY_EMAIL_FROM", "agents@helpdesk.local")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content(body)

    sink_path = EMAIL_DIR / f"{ticket['id']}-{int(time.time())}.eml"
    sink_path.write_bytes(msg.as_bytes())

    host = os.getenv("SMTP_HOST")
    smtp_ok = False
    smtp_error = None
    if host:
        try:
            port = int(os.getenv("SMTP_PORT", "1025"))
            with smtplib.SMTP(host, port, timeout=5) as smtp:
                if os.getenv("SMTP_USER"):
                    smtp.login(os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASS", ""))
                smtp.send_message(msg)
            smtp_ok = True
        except Exception as exc:  # noqa: BLE001 — notification must not break pipeline
            smtp_error = str(exc)

    return {
        "channel": "email",
        "to": to_addr,
        "file": str(sink_path),
        "smtpSent": smtp_ok,
        "smtpError": smtp_error,
    }


def post_webhook(ticket: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """HTTP webhook when WEBHOOK_URL is set; always mirror payload to disk."""
    import urllib.request

    WEBHOOK_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "event": "ai_run_completed",
        "ticketId": ticket["id"],
        "title": ticket["title"],
        "provider": result.get("provider"),
        "category": result.get("triage", {}).get("category"),
        "priority": result.get("triage", {}).get("priority"),
        "decision": result.get("decision"),
        "durationMs": result.get("durationMs"),
        "reportPath": result.get("reportPath"),
    }
    path = WEBHOOK_DIR / f"{ticket['id']}-{int(time.time())}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    url = os.getenv("WEBHOOK_URL")
    posted = False
    error = None
    if url:
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                posted = 200 <= resp.status < 300
        except Exception as exc:  # noqa: BLE001
            error = str(exc)

    return {
        "channel": "webhook",
        "url": url,
        "file": str(path),
        "posted": posted,
        "error": error,
    }


def notify(ticket: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        send_email_notification(ticket, result),
        post_webhook(ticket, result),
    ]
