"""Cognee-backed memory context for Verge findings."""

from .client import CogneeClient, CogneeResult, CogneeSettings
from .datasets import dataset_name
from .ingest import ingest_closed_finding, ingest_document
from .query import query_memory
from .retrieve import context_for_finding

__all__ = [
    "CogneeClient",
    "CogneeResult",
    "CogneeSettings",
    "context_for_finding",
    "dataset_name",
    "ingest_closed_finding",
    "ingest_document",
    "query_memory",
]

__version__ = "0.3.0"
