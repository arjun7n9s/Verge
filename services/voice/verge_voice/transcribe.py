"""Speechmatics batch transcription (Melia multilingual) + English ops text."""

from __future__ import annotations

import contextlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx
from verge_llm import LLMProvider, Message

from .languages import (
    MELIA_LANGUAGES,
    PLANT_RADIO_HINTS_DEFAULT,
    filter_hints,
    melia_language_catalog,
)

_TRUE = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class SpeechmaticsSettings:
    api_key: str | None = None
    base_url: str = "https://eu1.asr.api.speechmatics.com/v2"
    model: str = "melia-1"  # melia-1 | enhanced | standard
    language: str = "multi"  # Melia requires multi; enhanced/standard use ISO codes
    language_hints: tuple[str, ...] = PLANT_RADIO_HINTS_DEFAULT
    diarization: str = "speaker"
    translate_to_en: bool = True
    timeout_s: float = 60.0
    poll_interval_s: float = 0.5
    max_polls: int = 120  # Melia batch can take longer than short enhanced jobs

    @classmethod
    def from_env(cls, env: dict[str, str]) -> SpeechmaticsSettings:
        region = env.get("SPEECHMATICS_REGION", "eu1")
        base_url = env.get("SPEECHMATICS_BASE_URL") or (
            f"https://{region}.asr.api.speechmatics.com/v2"
        )
        model = (env.get("SPEECHMATICS_MODEL") or "melia-1").strip().lower()
        # Prefer explicit hints; fall back to SPEECHMATICS_LANGUAGES legacy list.
        hints_raw = env.get("SPEECHMATICS_LANGUAGE_HINTS") or env.get(
            "SPEECHMATICS_LANGUAGES", ""
        )
        if hints_raw.strip():
            hints, _ = filter_hints(hints_raw.split(","))
        else:
            hints = list(PLANT_RADIO_HINTS_DEFAULT)

        default_lang = "multi" if model == "melia-1" else "en"
        language = (env.get("SPEECHMATICS_LANGUAGE") or default_lang).strip().lower()
        if model == "melia-1" and language in {"auto", "en"}:
            # Melia rejects auto; bare "en" defeats multilingual — force multi.
            language = "multi"

        return cls(
            api_key=env.get("SPEECHMATICS_API_KEY"),
            base_url=base_url.rstrip("/"),
            model=model,
            language=language,
            language_hints=tuple(hints),
            diarization=(env.get("SPEECHMATICS_DIARIZATION") or "speaker").strip(),
            translate_to_en=env.get("SPEECHMATICS_TRANSLATE_TO_EN", "true").lower()
            in _TRUE,
            timeout_s=float(env.get("SPEECHMATICS_TIMEOUT_S", "60")),
            poll_interval_s=float(env.get("SPEECHMATICS_POLL_INTERVAL_S", "0.5")),
            max_polls=int(env.get("SPEECHMATICS_MAX_POLLS", "120")),
        )

    def missing_reason(self) -> str | None:
        if not self.api_key:
            return "missing SPEECHMATICS_API_KEY"
        return None

    def build_job_config(self) -> dict[str, Any]:
        transcription: dict[str, Any] = {
            "language": self.language,
            "diarization": self.diarization,
        }
        if self.model:
            transcription["model"] = self.model
        if self.model == "melia-1" and self.language_hints:
            transcription["language_hints"] = list(self.language_hints)

        config: dict[str, Any] = {
            "type": "transcription",
            "transcription_config": transcription,
        }

        # Melia does not support Speechmatics translation_config. For
        # enhanced/standard with a known non-English source, request EN.
        if (
            self.translate_to_en
            and self.model in {"enhanced", "standard"}
            and self.language not in {"en", "multi", "auto"}
        ):
            config["translation_config"] = {"target_languages": ["en"]}
        return config


def speechmatics_status(env: dict[str, str] | None = None) -> dict[str, Any]:
    """Config posture for ops/degradation (no network call — key presence only)."""
    settings = SpeechmaticsSettings.from_env(env or dict(os.environ))
    reason = settings.missing_reason()
    region = "eu1"
    if "asr.api.speechmatics.com" in settings.base_url:
        with contextlib.suppress(Exception):
            region = settings.base_url.split("//", 1)[1].split(".", 1)[0]
    return {
        "configured": reason is None,
        "degraded": reason is not None,
        "reason": reason,
        "model": settings.model,
        "language": settings.language,
        "region": region,
        "translateToEn": settings.translate_to_en,
    }


@dataclass(frozen=True)
class VoiceResult:
    transcript: str
    structured: dict[str, Any]
    degraded: bool = False
    reason: str | None = None
    provider: str = "speechmatics"
    job_id: str | None = None
    model: str | None = None
    transcript_original: str | None = None
    transcript_en: str | None = None
    languages_detected: tuple[str, ...] = ()
    translation_source: str | None = None  # none | identity | speechmatics | llm

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "transcript": self.transcript,
            "structured": self.structured,
            "degraded": self.degraded,
            "provider": self.provider,
            "languagesSupported": melia_language_catalog(),
            "plantRadioHints": list(PLANT_RADIO_HINTS_DEFAULT),
        }
        if self.job_id:
            body["jobId"] = self.job_id
        if self.reason:
            body["reason"] = self.reason
        if self.model:
            body["model"] = self.model
        if self.transcript_original is not None:
            body["transcriptOriginal"] = self.transcript_original
        if self.transcript_en is not None:
            body["transcriptEn"] = self.transcript_en
        if self.languages_detected:
            body["languagesDetected"] = list(self.languages_detected)
        if self.translation_source:
            body["translationSource"] = self.translation_source
        return body


def _empty_structured() -> dict[str, Any]:
    return {"summary": "", "hazards": [], "zones": [], "actions": []}


def _degraded(reason: str, *, model: str | None = None) -> VoiceResult:
    return VoiceResult(
        transcript="",
        structured=_empty_structured(),
        degraded=True,
        reason=reason,
        model=model,
    )


def _headers(settings: SpeechmaticsSettings) -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.api_key}"}


def _job_id(data: dict[str, Any]) -> str | None:
    for key in ("id", "job_id", "jobId"):
        if value := data.get(key):
            return str(value)
    job = data.get("job")
    if isinstance(job, dict):
        for key in ("id", "job_id", "jobId"):
            if value := job.get(key):
                return str(value)
    return None


def _job_status(data: dict[str, Any]) -> str:
    job = data.get("job", data)
    if isinstance(job, dict):
        return str(job.get("status", "")).lower()
    return ""


def _transcript_text(data: Any) -> str:
    if isinstance(data, str):
        return data.strip()
    if isinstance(data, dict):
        if isinstance(data.get("transcript"), str):
            return data["transcript"].strip()
        if isinstance(data.get("text"), str):
            return data["text"].strip()
        results = data.get("results")
        if isinstance(results, list):
            parts: list[str] = []
            for item in results:
                if not isinstance(item, dict):
                    continue
                if item.get("type") and item.get("type") not in {"word", "punctuation"}:
                    continue
                alternatives = item.get("alternatives") or []
                if alternatives and isinstance(alternatives[0], dict):
                    content = alternatives[0].get("content")
                    if content:
                        parts.append(str(content))
            return " ".join(parts).replace(" ,", ",").replace(" .", ".").strip()
    return ""


def _languages_from_transcript(data: Any) -> tuple[str, ...]:
    if not isinstance(data, dict):
        return ()
    found: list[str] = []
    for item in data.get("results") or []:
        if not isinstance(item, dict):
            continue
        alts = item.get("alternatives") or []
        if not alts or not isinstance(alts[0], dict):
            continue
        lang = alts[0].get("language")
        if isinstance(lang, str) and lang and lang not in found:
            found.append(lang)
    return tuple(found)


def _english_from_speechmatics_translations(data: Any) -> str | None:
    if not isinstance(data, dict):
        return None
    translations = data.get("translations")
    if not isinstance(translations, dict):
        return None
    en = translations.get("en")
    if isinstance(en, str) and en.strip():
        return en.strip()
    if isinstance(en, list):
        parts: list[str] = []
        for sent in en:
            if isinstance(sent, str):
                parts.append(sent)
            elif isinstance(sent, dict):
                content = sent.get("content") or sent.get("text")
                if content:
                    parts.append(str(content))
        joined = " ".join(parts).strip()
        return joined or None
    return None


_TRANSLATE_SYSTEM = (
    "You translate industrial radio / shift-handover speech to clear English. "
    "Preserve equipment tags, zone ids (e.g. B-04), permit ids, and hazard meaning. "
    "Output ONLY the English translation, no preamble."
)


def translate_to_english_llm(
    text: str, *, provider: LLMProvider | None, languages: tuple[str, ...]
) -> tuple[str | None, str | None]:
    """Return (english, reason_if_failed)."""
    if provider is None or not text.strip():
        return None, "no-llm-provider"
    lang_note = ", ".join(languages) if languages else "unknown"
    messages = [
        Message(role="system", content=_TRANSLATE_SYSTEM),
        Message(
            role="user",
            content=f"Detected languages: {lang_note}\n\nSource transcript:\n{text}",
        ),
    ]
    completion = provider.complete(messages, max_tokens=800, temperature=0.1)
    if completion.degraded or not completion.text.strip():
        return None, "llm-translate-degraded"
    return completion.text.strip(), None


def ensure_english_ops_text(
    *,
    original: str,
    languages: tuple[str, ...],
    sm_english: str | None,
    provider: LLMProvider | None,
    translate: bool,
) -> tuple[str, str]:
    """Pick English text for fusion + (translation_source)."""
    if not translate:
        return original, "none"
    non_en = [lng for lng in languages if lng and lng != "en"]
    if sm_english and sm_english.strip():
        return sm_english.strip(), "speechmatics"
    if not non_en:
        # Melia often omits tags on monolingual EN; treat as English.
        return original, "identity"
    english, err = translate_to_english_llm(original, provider=provider, languages=languages)
    if english:
        return english, "llm"
    # Last resort: keep original but mark reason in source for operators.
    return original, f"identity-fallback:{err or 'unknown'}"


def structure_handover(transcript: str) -> dict[str, Any]:
    text = transcript.strip()
    lower = text.lower()
    hazards = [
        name
        for name, tokens in {
            "gas": ("gas", "lel", "co ", "carbon monoxide", "smell"),
            "hot-work": ("hot work", "welding", "cutting"),
            "confined-space": ("confined space", "vessel entry", "entry permit"),
            "sensor-health": ("stale", "missing sensor", "stuck"),
        }.items()
        if any(token in lower for token in tokens)
    ]
    zones = sorted(
        {word.strip(".,:;") for word in text.split() if word[:1].isalpha() and "-" in word}
    )
    actions = []
    for marker in ("pause", "evacuate", "inspect", "escalate", "close permit"):
        if marker in lower:
            actions.append(marker)
    summary = text[:240]
    return {"summary": summary, "hazards": hazards, "zones": zones, "actions": actions}


_EXTRACTION_SYSTEM_PROMPT = (
    "Extract structured facts from an industrial shift-handover or near-miss "
    "transcript written in English. Reply with exactly four labeled lines, nothing else:\n"
    "summary: <one sentence>\n"
    "hazards: <comma-separated, from: gas, hot-work, confined-space, "
    "sensor-health, or none>\n"
    "zones: <comma-separated zone ids mentioned, or none>\n"
    "actions: <comma-separated, from: pause, evacuate, inspect, escalate, "
    "close permit, or none>\n"
    "Use only what the transcript actually says. Never invent a zone, hazard, "
    "or action that isn't there."
)


def _parse_extraction_lines(text: str) -> dict[str, Any] | None:
    fields: dict[str, str] = {}
    for raw in text.splitlines():
        if ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        key = key.strip().lower()
        if key in {"summary", "hazards", "zones", "actions"}:
            fields[key] = value.strip()
    if "summary" not in fields:
        return None

    def _csv(key: str) -> list[str]:
        raw = fields.get(key, "")
        if not raw or raw.lower() == "none":
            return []
        return [item.strip() for item in raw.split(",") if item.strip()]

    return {
        "summary": fields["summary"],
        "hazards": _csv("hazards"),
        "zones": _csv("zones"),
        "actions": _csv("actions"),
    }


def enrich_structured_with_llm(
    transcript: str, baseline: dict[str, Any], *, provider: LLMProvider | None
) -> dict[str, Any]:
    tagged_baseline = {**baseline, "source": "regex"}
    if provider is None or not transcript.strip():
        return tagged_baseline
    messages = [
        Message(role="system", content=_EXTRACTION_SYSTEM_PROMPT),
        Message(role="user", content=transcript),
    ]
    completion = provider.complete(messages, max_tokens=200)
    if completion.degraded or not completion.text.strip():
        return tagged_baseline
    parsed = _parse_extraction_lines(completion.text)
    if parsed is None:
        return tagged_baseline
    return {**parsed, "source": "llm"}


def transcribe_audio(
    audio: bytes,
    *,
    filename: str = "handover.wav",
    content_type: str = "application/octet-stream",
    provider: LLMProvider | None = None,
    env: dict[str, str] | None = None,
    client: httpx.Client | None = None,
    settings: SpeechmaticsSettings | None = None,
) -> VoiceResult:
    env = env or dict(os.environ)
    settings = settings or SpeechmaticsSettings.from_env(env)
    if reason := settings.missing_reason():
        return _degraded(reason, model=settings.model)
    if not audio:
        return _degraded("empty audio upload", model=settings.model)

    close_after = False
    http = client
    if http is None:
        http = httpx.Client(
            base_url=settings.base_url,
            headers=_headers(settings),
            timeout=settings.timeout_s,
        )
        close_after = True

    config = settings.build_job_config()
    try:
        create = http.post(
            "/jobs",
            data={"config": json.dumps(config)},
            files={"data_file": (filename, audio, content_type)},
        )
        create.raise_for_status()
        job_id = _job_id(create.json())
        if not job_id:
            return _degraded("speechmatics response missing job id", model=settings.model)

        for _ in range(settings.max_polls):
            detail = http.get(f"/jobs/{job_id}")
            detail.raise_for_status()
            status = _job_status(detail.json())
            if status == "done":
                transcript_resp = http.get(
                    f"/jobs/{job_id}/transcript", params={"format": "json-v2"}
                )
                transcript_resp.raise_for_status()
                payload = transcript_resp.json()
                original = _transcript_text(payload)
                languages = _languages_from_transcript(payload)
                sm_en = _english_from_speechmatics_translations(payload)
                english, translation_source = ensure_english_ops_text(
                    original=original,
                    languages=languages,
                    sm_english=sm_en,
                    provider=provider,
                    translate=settings.translate_to_en,
                )
                # Fusion / hazard extract always runs on English ops text.
                structured = enrich_structured_with_llm(
                    english, structure_handover(english), provider=provider
                )
                structured = {
                    **structured,
                    "languagesDetected": list(languages),
                    "translationSource": translation_source,
                }
                return VoiceResult(
                    transcript=english,
                    transcript_original=original,
                    transcript_en=english,
                    structured=structured,
                    degraded=False,
                    job_id=job_id,
                    model=settings.model,
                    languages_detected=languages,
                    translation_source=translation_source,
                    provider=f"speechmatics:{settings.model}",
                )
            if status in {"rejected", "error", "failed"}:
                return _degraded(
                    f"speechmatics job {job_id} {status}", model=settings.model
                )
            time.sleep(settings.poll_interval_s)
        return _degraded(
            f"speechmatics job {job_id} did not complete before timeout",
            model=settings.model,
        )
    except Exception as exc:
        return _degraded(f"speechmatics failed: {type(exc).__name__}", model=settings.model)
    finally:
        if close_after:
            http.close()


__all__ = [
    "MELIA_LANGUAGES",
    "SpeechmaticsSettings",
    "VoiceResult",
    "enrich_structured_with_llm",
    "melia_language_catalog",
    "structure_handover",
    "transcribe_audio",
]
