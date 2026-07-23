"""Paths, env defaults, and seed data."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
REPORT_DIR = OUTPUT_DIR / "reports"
EMAIL_DIR = OUTPUT_DIR / "emails"
WEBHOOK_DIR = OUTPUT_DIR / "webhooks"
EVAL_DIR = OUTPUT_DIR / "eval"
DB_PATH = Path(os.getenv("HELPDESK_DB", str(ROOT / "helpdesk.db")))

FALLBACK_HANDBOOK = """
IT: For WiFi and laptop connectivity, verify the corporate SSID, forget and
re-add the network, restart the wireless adapter, and check VPN status.
HR: Missing payslips and incorrect leave balances go to HR. Ask for the pay
period and employee ID. Never expose payroll details publicly.
FACILITIES: Standing desks, chairs, parking, and HVAC go to Facilities.
Water leaks are urgent and must be reported immediately.
""".strip()

DEFAULT_TICKETS: list[dict[str, Any]] = [
    {
        "id": "HD-101",
        "title": "Office WiFi disconnects",
        "description": "My laptop drops the office WiFi every few minutes.",
        "category": "IT",
        "priority": "MEDIUM",
        "status": "OPEN",
        "submitter": "Employee Demo",
        "assignee": None,
    },
    {
        "id": "HD-102",
        "title": "Missing March payslip",
        "description": "The March payslip is missing from my portal.",
        "category": "HR",
        "priority": "MEDIUM",
        "status": "IN_PROGRESS",
        "submitter": "Employee Demo",
        "assignee": "Support Demo",
    },
    {
        "id": "HD-103",
        "title": "Water leak at reception",
        "description": "Water is leaking from the ceiling above reception.",
        "category": "FACILITIES",
        "priority": "URGENT",
        "status": "RESOLVED",
        "submitter": "Another Employee",
        "assignee": "Support Demo",
    },
]
