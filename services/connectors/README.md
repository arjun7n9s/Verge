# verge-connectors — the integration hub

Connectors read from external plant systems and emit **canonical Verge events**
(the same `reading` / `permit` / `shift` dicts the edge plane produces), so
everything downstream sees one shape regardless of source (spec §14 Phase 4).

| Connector | Kind | Status | Source |
|-----------|------|--------|--------|
| `csv-historian` | historian | **real** | `tag,ts,value` CSV + tag map |
| `csv-cmms` | CMMS | **real** | permit CSV export |
| `pi` | historian | degraded stub | OSIsoft PI Web API |
| `phd` | historian | degraded stub | Honeywell PHD |
| `maximo` | CMMS | degraded stub | IBM Maximo |
| `sap-pm` | CMMS | degraded stub | SAP PM |
| `milestone` | VMS | degraded stub | Milestone (feeds `verge-vision`) |

## Two rules

- **Degrade, never fabricate (P4).** No config / no network / no creds →
  `ConnectorResult(events=[], degraded=True, reason=...)`. Proprietary
  connectors default to degraded on the dev/air-gapped box.
- **Unmapped is dropped, not guessed (P3).** A historian tag with no mapping to
  a commissioned sensor is skipped and counted, never assigned to a guessed zone.

## CLI

`verge ingest` emits one canonical event per line — pipeable straight into the
risk engine, exactly like `verge sim`:

```bash
# bundled demos (no env needed):
verge ingest --demo historian | python -m verge_risk
verge ingest --demo cmms

# env-configured connector:
VERGE_CONNECTOR=csv-historian \
VERGE_HISTORIAN_CSV=readings.csv \
VERGE_HISTORIAN_TAGMAP=tags.json \
  verge ingest --connector csv-historian --since 2025-01-14T06:00:00
```

## Env

```bash
VERGE_CONNECTOR=csv-historian            # default connector for connector_from_env()
VERGE_HISTORIAN_CSV=/data/readings.csv
VERGE_HISTORIAN_TAGMAP=/etc/verge/tags.json
VERGE_CMMS_CSV=/data/permits.csv
VERGE_PI_WEB_API_URL=https://pi.plant/piwebapi     # pi
VERGE_PHD_URL=...            VERGE_MAXIMO_URL=...    VERGE_SAP_PM_URL=...
VERGE_MILESTONE_URL=...
```

## Formats

**Historian tag map** (`tag → {sensorId, kind, unit, zoneId}`) and
**readings CSV** (`tag,ts,value`) — see `verge_connectors/samples/`.

**CMMS permits CSV**: `permitId,kind,zoneId,equipmentId,validFrom,validTo`.
