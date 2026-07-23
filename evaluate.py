#!/usr/bin/env python3
"""Golden-set evaluation harness (rubric: Testing & Evaluation).

Usage:
  python evaluate.py              # mock provider (fast, CI-friendly)
  EVAL_PROVIDER=ollama python evaluate.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from streamlit_app import (
    MockProvider,
    normalize_category,
    run_multi_agent,
    select_provider,
)

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "outputs" / "eval"

GOLDEN_CASES = [
    {
        "id": "g1",
        "title": "WiFi keeps dropping",
        "description": "Laptop disconnects from office WiFi every few minutes.",
        "expectedCategory": "IT",
    },
    {
        "id": "g2",
        "title": "Need VPN for contractor",
        "description": "Please provision VPN credentials before Monday.",
        "expectedCategory": "IT",
    },
    {
        "id": "g3",
        "title": "Printer jam on floor 3",
        "description": "Finance printer shows paper jam even when tray is empty.",
        "expectedCategory": "IT",
    },
    {
        "id": "g4",
        "title": "Missing March payslip",
        "description": "Payslip for March is not visible in the portal.",
        "expectedCategory": "HR",
    },
    {
        "id": "g5",
        "title": "Leave balance looks wrong",
        "description": "Portal shows 3 PTO days but I should have 8.",
        "expectedCategory": "HR",
    },
    {
        "id": "g6",
        "title": "Onboarding for new hire",
        "description": "New engineer starts July 15 — need laptop and badge.",
        "expectedCategory": "HR",
    },
    {
        "id": "g7",
        "title": "Standing desk request",
        "description": "Need a height-adjustable desk for ergonomic reasons.",
        "expectedCategory": "FACILITIES",
    },
    {
        "id": "g8",
        "title": "Broken chair near kitchen",
        "description": "Chair has a loose wheel and nearly tipped over.",
        "expectedCategory": "FACILITIES",
    },
    {
        "id": "g9",
        "title": "Water leak at reception",
        "description": "Ceiling leak above the front desk — urgent facilities check.",
        "expectedCategory": "FACILITIES",
    },
    {
        "id": "g10",
        "title": "Expense report stuck",
        "description": "Travel expenses still pending with no approver listed.",
        "expectedCategory": "OTHER",
    },
    {
        "id": "g11",
        "title": "Software installation blocked",
        "description": "The laptop software installer requires administrator access.",
        "expectedCategory": "IT",
    },
    {
        "id": "g12",
        "title": "Parking pass replacement",
        "description": "My office parking badge was damaged and needs replacement.",
        "expectedCategory": "FACILITIES",
    },
]


def main() -> int:
    preference = os.getenv("EVAL_PROVIDER", "mock")
    try:
        provider = select_provider(preference if preference != "mock" else "mock")
    except Exception as exc:  # noqa: BLE001
        print(f"Provider '{preference}' unavailable ({exc}); using mock.")
        provider = MockProvider()

    started = time.perf_counter()
    correct = valid = completed = 0
    rows: list[dict] = []
    history: list[dict] = []

    for case in GOLDEN_CASES:
        case_start = time.perf_counter()
        ticket = {
            "id": case["id"],
            "title": case["title"],
            "description": case["description"],
            "category": "OTHER",
            "priority": None,
            "status": "OPEN",
            "submitter": "Eval",
            "assignee": None,
        }
        try:
            result = run_multi_agent(
                ticket,
                history,
                provider,
                persist=False,
                notify_actions=False,
            )
            predicted = normalize_category(result["triage"].get("category"))
            valid += 1
            ok = predicted == case["expectedCategory"]
            if ok:
                correct += 1
            completed += 1
            rows.append(
                {
                    "id": case["id"],
                    "expected": case["expectedCategory"],
                    "predicted": predicted,
                    "correct": ok,
                    "confidence": result["triage"].get("confidence"),
                    "multiStepCompleted": True,
                    "evaluatorApproved": bool(
                        result.get("evaluation", {}).get("approved")
                    ),
                    "durationMs": round((time.perf_counter() - case_start) * 1000),
                }
            )
        except Exception as exc:  # noqa: BLE001
            rows.append(
                {
                    "id": case["id"],
                    "expected": case["expectedCategory"],
                    "predicted": None,
                    "correct": False,
                    "multiStepCompleted": False,
                    "error": str(exc),
                    "durationMs": round((time.perf_counter() - case_start) * 1000),
                }
            )

    total = len(GOLDEN_CASES)
    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "provider": provider.name,
        "total": total,
        "validOutputs": valid,
        "validOutputRate": valid / total,
        "categoryAccuracy": correct / total,
        "successfulMultiStepCompletions": completed,
        "multiStepCompletionRate": completed / total,
        "durationMs": round((time.perf_counter() - started) * 1000),
        "cases": rows,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = provider.name.replace("/", "-").replace(":", "-")
    named = OUT_DIR / f"evaluation-report-{stamp}.json"
    latest = OUT_DIR / "evaluation-report.json"
    named.write_text(json.dumps(report, indent=2), encoding="utf-8")
    latest.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("Evaluation complete")
    print(f"  Cases: {report['total']}")
    print(f"  Valid output rate: {report['validOutputRate'] * 100:.1f}%")
    print(f"  Category accuracy: {report['categoryAccuracy'] * 100:.1f}%")
    print(f"  Multi-step completion: {report['multiStepCompletionRate'] * 100:.1f}%")
    print(f"  Wrote {named}")

    min_acc = float(os.getenv("EVAL_MIN_ACCURACY", "0.7"))
    min_valid = float(os.getenv("EVAL_MIN_VALID_RATE", "0.8"))
    min_complete = float(os.getenv("EVAL_MIN_COMPLETION_RATE", "0.8"))
    if (
        report["categoryAccuracy"] < min_acc
        or report["validOutputRate"] < min_valid
        or report["multiStepCompletionRate"] < min_complete
    ):
        print(
            "Evaluation thresholds FAILED: "
            f"accuracy>={min_acc}, valid>={min_valid}, completion>={min_complete}",
            file=sys.stderr,
        )
        return 1
    print("Evaluation thresholds PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
