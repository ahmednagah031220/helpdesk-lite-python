"""HelpDesk Lite — multi-agent IT / HR / Facilities triage."""

__version__ = "1.1.0"

from helpdesk.orchestrator import run_multi_agent, status_metrics
from helpdesk.providers import MockProvider, OllamaProvider, select_provider
from helpdesk.retrieval import HANDBOOK_CHUNKS, normalize_category, normalize_priority

__all__ = [
    "HANDBOOK_CHUNKS",
    "MockProvider",
    "OllamaProvider",
    "normalize_category",
    "normalize_priority",
    "run_multi_agent",
    "select_provider",
    "status_metrics",
    "__version__",
]
