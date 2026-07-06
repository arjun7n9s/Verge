"""Factory helpers for API state backends."""

from __future__ import annotations

import os

from sqlalchemy.engine import Engine

from .factory import make_store
from .permits_registry import PermitRegistry
from .reading_buffer import ReadingBuffer
from .store_base import StoreProtocol


def store_engine(store: StoreProtocol) -> Engine | None:
    engine = getattr(store, "engine", None)
    return engine if isinstance(engine, Engine) else None


def make_permits_registry(
    env: dict[str, str] | None = None,
    store: StoreProtocol | None = None,
) -> PermitRegistry:
    env = env if env is not None else dict(os.environ)
    store = store or make_store(env)
    return PermitRegistry(store_engine(store))


def make_reading_buffer(
    env: dict[str, str] | None = None,
    store: StoreProtocol | None = None,
) -> ReadingBuffer:
    env = env if env is not None else dict(os.environ)
    store = store or make_store(env)
    return ReadingBuffer(store_engine(store))
