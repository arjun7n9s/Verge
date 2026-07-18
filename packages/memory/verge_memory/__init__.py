"""Cognee-backed memory context for Verge findings."""

from .client import CogneeClient, CogneeResult, CogneeSettings, cognee_enabled_from_env
from .datasets import dataset_name
from .ingest import ingest_and_cognify, ingest_closed_finding, ingest_document, ingest_feedback
from .query import query_memory
from .retrieve import context_for_finding
from .status import dataset_health

__all__ = [
    "CogneeClient",
    "CogneeResult",
    "CogneeSettings",
    "cognee_enabled_from_env",
    "context_for_finding",
    "dataset_health",
    "dataset_name",
    "ingest_and_cognify",
    "ingest_closed_finding",
    "ingest_document",
    "ingest_feedback",
    "query_memory",
]

__version__ = "0.3.0"
