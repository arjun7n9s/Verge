# Day-2 operability — the plant-IT surface (spec §14.6)

Plant IT and safety operators are **different users with different surfaces**.
The operator works findings in the Console. Plant IT keeps the box healthy — and
never has to log into the safety console to do it.

## Two endpoints, distinct from the Console

| Endpoint | Format | For |
|----------|--------|-----|
| `GET /metrics` | Prometheus text exposition | Prometheus scrape → Grafana |
| `GET /api/ops/status` | JSON | dashboards, scripts, health checks |

Both are **dependency-free** — the Prometheus exporter emits the stable text
format directly, so no extra library is needed on an air-gapped box (P2).

A ready-to-import Grafana dashboard and a Prometheus scrape config (with audit-
chain-broken / ingest-stalled alert rules) live in
[`deploy/observability/`](../deploy/observability/).

## What it reports

- **Audit chain integrity** — entries, head hash, and `verified` (the chain is
  re-walked; a tampered row shows `verified: false`). This is the most
  legally-sensitive signal in the system (P6).
- **Ingest health** — distinct sensors seen, buffered reading points, last
  reading timestamp.
- **Sensor-health rollup** — counts by data quality (`live` / `stale` /
  `stuck-at-value` / `missing`), and live %.
- **Degradation posture** — `llm.degraded`, `vision.degraded` (the safety core
  is never gated on either; §10.6).
- **Version / model registry** — build version, model registry version.
- **Backup + signed bundle** — last backup time and signed-bundle age, from the
  deploy environment (`VERGE_LAST_BACKUP_TS`, `VERGE_BUNDLE_BUILT_TS`).
- **Last replay run** — when the eval harness last produced measured numbers.

## Honesty rule

A fact the box cannot measure is reported as `null`, and the corresponding
Prometheus metric is **omitted entirely** — never emitted as a fabricated `0` or
a fake timestamp. A box that has never run a backup reports `backup.lastTs:
null`; that is a real, actionable state, not an error to paper over (P4).

```bash
# Prometheus scrape config (plant IT):
#   - job_name: verge
#     metrics_path: /metrics
#     static_configs: [{ targets: ["verge-api:8000"] }]

curl -s http://localhost:8000/metrics
curl -s http://localhost:8000/api/ops/status | jq
```

## Backup + restore verification (§14.6)

The audit chain is the most legally-sensitive artifact, so a restore is not
trusted until it is **replayed and re-verified**.

```bash
verge backup create --out audit-snapshot.json     # export the chain
verge backup verify --file audit-snapshot.json     # replay + verify
# API equivalents:
curl -s http://localhost:8000/api/ops/backup > snap.json
curl -s -XPOST http://localhost:8000/api/ops/backup/verify \
  -H 'content-type: application/json' -d @snap.json
```

Verification rebuilds the chain from the snapshot rows and walks the hashes; a
linkage break, a head mismatch, or a content-hash mismatch **rejects** the
snapshot (P6). Timestamps are normalized to canonical form first, so a snapshot
verifies regardless of how it was serialized (`…Z` vs `…+00:00`).

## Metrics reference

| Metric | Meaning |
|--------|---------|
| `verge_build_info{version}` | build/version info (always `1`) |
| `verge_uptime_seconds` | process uptime |
| `verge_audit_entries` | audit chain length |
| `verge_audit_verified` | `1` chain intact, `0` broken |
| `verge_findings_total` | findings on record |
| `verge_ingest_sensors` | distinct sensors seen |
| `verge_ingest_readings` | buffered reading points |
| `verge_llm_degraded` | LLM narrative layer degraded |
| `verge_vision_degraded` | vision plane degraded |
| `verge_sensor_health{quality}` | sensors by data-quality state |
| `verge_backup_age_seconds` | age of last backup (omitted if unknown) |
| `verge_signed_bundle_age_seconds` | age of installed signed bundle (omitted if unknown) |
