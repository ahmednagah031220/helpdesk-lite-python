"""LLM providers — Ollama HTTP API and deterministic mock."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


def _contains_any(text: str, words: tuple[str, ...]) -> bool:
    """Whole-word / phrase match so 'pto' does not hit 'laptop'."""
    for word in words:
        if " " in word:
            if word in text:
                return True
        elif re.search(rf"\b{re.escape(word)}\b", text):
            return True
    return False


@dataclass
class MockProvider:
    name: str = "mock"

    def complete(self, system: str, user: str) -> dict[str, Any]:
        text = user.lower()
        system_l = system.lower()
        if "triage" in system_l:
            if _contains_any(
                text,
                ("payslip", "leave", "payroll", "onboarding", "new hire", "pto"),
            ):
                category, priority = "HR", "MEDIUM"
            elif _contains_any(
                text,
                (
                    "wifi",
                    "vpn",
                    "printer",
                    "software",
                    "administrator",
                    "laptop",
                ),
            ):
                category, priority = "IT", "MEDIUM"
            elif _contains_any(
                text,
                ("leak", "desk", "chair", "hvac", "parking", "facilities"),
            ):
                category = "FACILITIES"
                priority = "URGENT" if _contains_any(text, ("leak",)) else "LOW"
            else:
                category, priority = "OTHER", "MEDIUM"
            return {
                "category": category,
                "priority": priority,
                "confidence": 0.86,
                "rationale": "Deterministic demo classification.",
                "tags": [category.lower()],
            }
        if "knowledge" in system_l:
            return {
                "relevant": True,
                "summary": "Relevant handbook guidance was retrieved from the knowledge base.",
                "suggestedSteps": [
                    "Confirm the reported details",
                    "Apply the matching handbook checklist",
                    "Escalate if the issue persists",
                ],
                "citations": [],
            }
        if "evaluator" in system_l:
            return {
                "approved": True,
                "confidence": 0.9,
                "issues": [],
                "notes": "Draft is safe, useful, and requires human approval.",
            }
        return {
            "draftResponse": (
                "Thanks for reporting this. We reviewed similar tickets and the "
                "internal handbook. A support teammate will confirm the suggested "
                "steps before applying any ticket changes."
            ),
            "recommendedActions": [
                "Review the drafted response",
                "Confirm category and priority",
            ],
            "needsHumanReview": True,
            "confidence": 0.82,
        }


@dataclass
class OllamaProvider:
    base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    timeout: float = 120.0

    @property
    def name(self) -> str:
        return f"ollama:{self.model}"

    def complete(self, system: str, user: str) -> dict[str, Any]:
        payload = json.dumps(
            {
                "model": self.model,
                "stream": False,
                "format": "json",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "options": {"temperature": 0.2},
            }
        ).encode()
        req = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read())
        content = body.get("message", {}).get("content") or body.get("response")
        if not content:
            raise ValueError("Ollama returned empty content")
        return json.loads(content)


def select_provider(preference: str = "auto"):
    if preference == "mock":
        return MockProvider()
    provider = OllamaProvider()
    try:
        req = urllib.request.Request(f"{provider.base_url.rstrip('/')}/api/tags")
        with urllib.request.urlopen(req, timeout=2):
            return provider
    except (OSError, urllib.error.URLError):
        if preference == "ollama":
            raise
        return MockProvider()
