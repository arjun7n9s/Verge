# Plant-IT observability (spec §14.6)

The Verge API exposes Prometheus metrics at `/metrics` (dependency-free text
exposition) — the plant IT team's surface, **distinct from the operator
console**. This directory has the scrape config and a Grafana dashboard so IT
sees ingest rate, sensor-health rollup, audit-chain integrity, degradation
posture, and model registry state without ever logging into the safety console.

## Files

- [`prometheus.yml`](prometheus.yml) — scrape config for the Verge API + two
  suggested alert rules (audit-chain broken, ingest stalled).
- [`grafana-verge-plant-it.json`](grafana-verge-plant-it.json) — importable
  Grafana dashboard (Dashboards → Import → upload).

## Quick local run

```bash
# with the API on :8000
docker run -p 9090:9090 -v "$PWD/deploy/observability/prometheus.yml:/etc/prometheus/prometheus.yml" prom/prometheus
docker run -p 3000:3000 grafana/grafana   # then import the dashboard JSON
```

Point the dashboard's Prometheus datasource at your Prometheus, and adjust the
scrape target (`api:8000`) to match your deployment.

## Metrics

See [`docs/operations.md`](../../docs/operations.md#metrics-reference) for the
full metric reference (`verge_audit_verified`, `verge_ingest_readings`,
`verge_sensor_health{quality}`, `verge_models_total`, …).
