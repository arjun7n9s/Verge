# deploy/

Single-box dev / hackathon stack (spec §8). Production is the same services on
K3s in the OT-DMZ with the LLM provider swapped to on-prem Ollama/vLLM and no
egress.

```bash
cp .env.example .env      # from repo root; or edit deploy/.env
make up                   # infra only (docker compose up -d)
make up-app               # infra + API + console (builds images)
make logs                 # tail
make down
```

### Full stack (M7)

`make up-app` starts everything including:

| Service | Port | Purpose |
|---------|------|---------|
| verge-api | 8000 | FastAPI gateway (SQL store → Postgres) |
| verge-console | 8088 | Operator console (nginx → API proxy) |
| Keycloak | 8080 | OIDC (`verge` realm, user `sarah` / `verge`) |

Pilot login (Keycloak dev import): **sarah** / **verge** with role `Safety_Engineer`.

To enable OIDC on the API, set `VERGE_AUTH_ENABLED=true` in `deploy/.env` and
rebuild/restart `verge-api`. The console picks up Keycloak when built with
`VITE_KEYCLOAK_URL` (set automatically in compose for `verge-console`).

### Durable API mode (M9)

With infra up, run the API against Postgres so findings, permits, readings, and
audit survive restarts:

```bash
# Set POSTGRES_PASSWORD in deploy/.env first, then:
make up
make dev-sql    # VERGE_STORE=sql against localhost:5432/verge
```

Permits and sensor readings persist in the same DB as findings when
`VERGE_STORE=sql`. Timescale (`5433`) is for high-volume OT telemetry at scale;
the API buffer uses the SQL store table for pilot/dev parity.

### Edge gateway → API

Forward MQTT-normalized events directly to the API (alongside Redpanda):

```bash
uv run python -m verge_edge.gateway --mqtt localhost --post-api http://localhost:8000
```

| Service | Port | Purpose |
|---------|------|---------|
| Redpanda | 19092 | canonical event spine (Kafka API) |
| Postgres + PostGIS | 5432 | permits, plant layout, geo zones, audit |
| TimescaleDB | 5433 | sensor time-series, rate-of-rise features |
| Neo4j | 7474/7687 | compound-risk knowledge graph |
| MinIO | 9000/9001 | evidence packs, frames, reports |
| Redis | 6379 | jobs / SSE fan-out |
| Keycloak | 8080 | OIDC / RBAC |

`initdb/` runs once on first volume create: PostGIS extension + core tables,
Timescale hypertable + 1-minute continuous aggregate. The `audit_entry` table is
append-only by convention (P6) — application code never issues UPDATE/DELETE
against it.

`deploy/keycloak/verge-realm.json` is imported on first Keycloak start.
