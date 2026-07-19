"""Faster-Whisper offline fallback when Speechmatics is down (Phase 2C).

Optional path: only runs when ``VERGE_WHISPER_ENABLED`` is truthy and the
``faster-whisper`` package (or an injected runner) is available. Never
fabricates a transcript — missing model / empty audio → degraded empty.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

_TRUE = {"1", "true", "yes", "on"}


class WhisperRunner(Protocol):
    def __call__(self, audio: bytes, *, filename: str, model: str) -> str: ...


@dataclass(frozen=True)
class WhisperSettings:
    enabled: bool = False
    model: str = "tiny"
    device: str = "cpu"
    compute_type: str = "int8"

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> WhisperSettings:
        env = env or dict(os.environ)
        return cls(
            enabled=env.get("VERGE_WHISPER_ENABLED", "false").lower() in _TRUE,
            model=(env.get("VERGE_WHISPER_MODEL") or "tiny").strip(),
            device=(env.get("VERGE_WHISPER_DEVICE") or "cpu").strip(),
            compute_type=(env.get("VERGE_WHISPER_COMPUTE_TYPE") or "int8").strip(),
        )


def whisper_status(env: dict[str, str] | None = None) -> dict[str, Any]:
    settings = WhisperSettings.from_env(env)
    if not settings.enabled:
        return {
            "enabled": False,
            "available": False,
            "reason": "VERGE_WHISPER_ENABLED not set",
            "model": settings.model,
        }
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return {
            "enabled": True,
            "available": False,
            "reason": "faster-whisper not installed",
            "model": settings.model,
        }
    return {
        "enabled": True,
        "available": True,
        "reason": None,
        "model": settings.model,
        "device": settings.device,
    }


def _default_runner(audio: bytes, *, filename: str, model: str) -> str:
    from faster_whisper import WhisperModel

    settings = WhisperSettings.from_env()
    suffix = Path(filename).suffix or ".wav"
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(audio)
        wm = WhisperModel(
            model or settings.model,
            device=settings.device,
            compute_type=settings.compute_type,
        )
        segments, _info = wm.transcribe(path, beam_size=1)
        parts = [seg.text.strip() for seg in segments if seg.text and seg.text.strip()]
        return " ".join(parts).strip()
    finally:
        with contextlib.suppress(OSError):
            os.unlink(path)


def transcribe_with_whisper(
    audio: bytes,
    *,
    filename: str = "handover.wav",
    env: dict[str, str] | None = None,
    runner: WhisperRunner | Callable[..., str] | None = None,
) -> tuple[str | None, str | None]:
    """Return ``(transcript, None)`` on success or ``(None, reason)`` on failure."""
    env = env or dict(os.environ)
    settings = WhisperSettings.from_env(env)
    if not settings.enabled:
        return None, "whisper-disabled"
    if not audio:
        return None, "empty audio upload"
    run = runner or _default_runner
    try:
        text = run(audio, filename=filename, model=settings.model)
    except Exception as exc:  # noqa: BLE001 — degrade, never raise to STT caller
        return None, f"whisper failed: {type(exc).__name__}"
    if not (text or "").strip():
        return None, "whisper empty transcript"
    return text.strip(), None


__all__ = [
    "WhisperSettings",
    "transcribe_with_whisper",
    "whisper_status",
]
