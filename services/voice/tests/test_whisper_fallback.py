"""Faster-Whisper fallback when Speechmatics is unavailable."""

from verge_voice.transcribe import speechmatics_status, transcribe_audio
from verge_voice.whisper_fallback import whisper_status


def test_whisper_status_disabled_by_default() -> None:
    st = whisper_status({})
    assert st["enabled"] is False
    assert st["available"] is False


def test_missing_speechmatics_still_silent_without_whisper() -> None:
    body = transcribe_audio(b"audio-bytes", env={}).to_dict()
    assert body["degraded"] is True
    assert body["transcript"] == ""


def test_whisper_fallback_when_speechmatics_missing() -> None:
    def fake_runner(audio: bytes, *, filename: str, model: str) -> str:
        assert audio
        assert model == "tiny"
        return "gas smell near battery B-04"

    body = transcribe_audio(
        b"fake-wav",
        env={"VERGE_WHISPER_ENABLED": "true", "VERGE_WHISPER_MODEL": "tiny"},
        whisper_runner=fake_runner,
    ).to_dict()
    assert body["degraded"] is False
    assert "gas" in body["transcript"].lower()
    assert body["provider"] == "faster-whisper"
    assert "gas" in body["structured"]["hazards"]


def test_speechmatics_status_includes_whisper_block() -> None:
    st = speechmatics_status({"SPEECHMATICS_API_KEY": "k"})
    assert "whisperFallback" in st
    assert st["configured"] is True
