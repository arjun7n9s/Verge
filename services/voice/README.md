# verge-voice

Speechmatics-backed handover and near-miss transcription for Verge.

The package degrades instead of raising when credentials are missing or the API
is unavailable. This keeps the safety core and API responsive even when cloud
speech services are down.

## Environment

```bash
SPEECHMATICS_API_KEY=...
SPEECHMATICS_REGION=eu1
SPEECHMATICS_LANGUAGE=en
```

`SPEECHMATICS_BASE_URL` can override the region-derived default:
`https://eu1.asr.api.speechmatics.com/v2`.

## API Examples

```bash
curl -F "file=@handover.wav" http://localhost:8000/api/voice/transcribe
curl -F "file=@handover.wav" -F "actor=maya" http://localhost:8000/api/voice/handover
```
