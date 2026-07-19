# verge-voice

Speechmatics-backed radio / handover / near-miss transcription for Verge.

Default path: **Melia-1** multilingual batch ASR → **English ops text** →
structured hazards/zones/actions (regex + optional aimlapi extract).

## Why Melia + aimlapi English

- Melia code-switches across 50+ languages (EN/HI/TA plant radio).
- Melia does **not** support Speechmatics `translation_config`.
- Verge therefore translates to English with **aimlapi** when non-English is
  detected, then runs hazard extraction on the English text for fusion.

## Environment

```bash
SPEECHMATICS_API_KEY=...
SPEECHMATICS_BASE_URL=https://eu1.asr.api.speechmatics.com/v2   # EU or US for Melia
SPEECHMATICS_MODEL=melia-1
SPEECHMATICS_LANGUAGE=multi
SPEECHMATICS_LANGUAGE_HINTS=en,hi,ta,ur,bn,mr
SPEECHMATICS_TRANSLATE_TO_EN=true

# Optional offline fallback (Phase 2C degrade path)
VERGE_WHISPER_ENABLED=false   # set true + install faster-whisper
VERGE_WHISPER_MODEL=tiny
```

When Speechmatics is missing or fails and Whisper is enabled, `transcribe_audio`
returns a Faster-Whisper transcript (`provider: faster-whisper`). Otherwise it
returns silent degraded voice and ops banners tell the operator — risk still runs.

## Languages

`GET /api/voice/languages` returns the full Melia catalog.

**Plant-radio hints (supported):** English (`en`), Hindi (`hi`), Tamil (`ta`),
Urdu (`ur`), Bengali (`bn`), Marathi (`mr`).

**Not in Speechmatics Melia table today:** Telugu (`te`), Kannada (`kn`) — do
not expect reliable ASR for those until Speechmatics adds them.

Full list: see `verge_voice/languages.py` (sourced from
https://docs.speechmatics.com/speech-to-text/languages).

## API

```bash
curl http://localhost:8000/api/voice/languages

curl -F "file=@radio.wav" http://localhost:8000/api/voice/transcribe
# → transcript (English ops), transcriptOriginal, languagesDetected,
#   translationSource, structured hazards/zones/actions

curl -F "file=@handover.wav" -F "actor=maya" http://localhost:8000/api/voice/handover
curl -F "file=@near-miss.wav" -F "actor=maya" http://localhost:8000/api/voice/near-miss
```

## Degrade behavior

Missing key / API failure → `degraded: true`, empty transcript, never invented
speech. LLM translate/extract failures fall back to original text + regex
structure.
