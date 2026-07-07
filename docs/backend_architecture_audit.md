# Verge Backend Architecture Audit

Date: 2026-07-07  
Scope: backend, data plane, services, edge/ingestion, deployment, operations, security. Frontend intentionally excluded.

## Executive Verdict

Verge has moved from a narrow prototype into a broad backend skeleton: risk engine, durable API store, contracts, MLOps registry, compliance, vision, connectors, digital twin, Redpanda, Postgres/PostGIS, Timescale, Neo4j, MinIO, Keycloak, Prometheus/Grafana, OTel collector, Docker/K8s manifests, and a strong test suite.

The system is internally consistent: `uv run pytest -q` passed 324 tests and `uv run ruff check .` passed. The remaining gap is production shape. Several modules are intentionally honest stubs or pilot-grade implementations. That is acceptable for Horizon-1 demos, but not yet ready for an industrial deployment where outage, replay, bad data, auth mistakes, audit disputes, and network partitions are normal.

## Highest-Risk Findings

### 1. Security Boundary Is Development-Grade

Evidence:

- `services/api/verge_api/main.py:89` allows all CORS origins, methods, and headers.
- `services/api/verge_api/auth.py:21` leaves auth disabled unless `VERGE_AUTH_ENABLED=true`.
- `services/api/verge_api/auth.py:50` validates issuer but disables audience verification.
- `deploy/k8s/configmap.yaml:12` sets `VERGE_AUTH_ENABLED: "false"`.
- `deploy/keycloak/verge-realm.json:23` enables direct access grants; `:46` includes a demo password.

Risk: every API route, including lifecycle transitions, responses, alert previews, findings, permits, readings, reports, backup export, memory, and vision, is effectively unauthenticated in the default cluster manifest. Even when auth is enabled, there is no route-level RBAC/ABAC in the API and no audience enforcement.

Target state:

- Make auth mandatory outside local dev.
- Validate issuer, audience, expiry, client, and token type.
- Enforce route-level roles/scopes: safety engineer, supervisor, plant manager, admin, service account.
- Move secrets to Kubernetes `Secret`, disable demo credentials, turn off direct grants for browser clients unless explicitly required.
- Add rate limits, request size limits, audit attribution from token subject, and object-level authorization.
- Add Kubernetes NetworkPolicies and mTLS/service-to-service auth for API, risk-engine, Redpanda, Postgres, Timescale, Neo4j, MinIO.

Comparable systems: Keycloak Authorization Services support resource-server policies; OWASP API Security lists broken object-level auth and broken authentication as top API risks.

### 2. Risk Streaming Is Explainable But Not Yet a Production Stream Processor

Evidence:

- `services/risk-engine/verge_risk/runner.py:61` appends permits forever in process state.
- `services/risk-engine/verge_risk/runner.py:118` keeps dedupe state only in memory.
- `services/risk-engine/verge_risk/runner.py:159` uses a fixed consumer group and `auto.offset.reset=latest`.
- `services/risk-engine/verge_risk/runner.py:142` dedupes by `(zone, sorted(lineage))`, not event id, window, rule version, or source offset.
- `services/risk-engine/verge_risk/cep.py` is a hand-rolled sliding window, not an event-time CEP engine with watermarks, late-event handling, checkpoints, and partitioned durable state.

Risk: restarts can re-emit or miss findings; late/out-of-order OT data can change historical truth without deterministic correction; scaling beyond one worker is unsafe; permit state can leak across validity windows unless all downstream filters are perfect.

Target state:

- Add event IDs, source offsets, schema version, site ID, and ingestion timestamp to every canonical event.
- Persist dedupe/finding emission state keyed by event-time windows.
- Use Redpanda/Kafka consumer lag metrics, explicit offset commits after durable writes, retry topics, and DLQs.
- For advanced architecture, move compound temporal correlation to Flink CEP or an equivalent stateful event-time engine; keep the deterministic Python rules as a library used by that engine.
- Define processing semantics per output: at-least-once with idempotent sinks for pilot; exactly-once/transactional where safety/legal evidence requires it.

Comparable systems: Apache Flink models event time/watermarks and CEP over endless streams; Kafka documents delivery semantics and exactly-once processing requires cooperation between broker and application.

### 3. Audit Chain Is Tamper-Evident, Not Yet Regulator-Grade Immutable Evidence

Evidence:

- `packages/audit/verge_audit/chain.py:135` rebuilds the chain from stored rows.
- `services/api/verge_api/sql_store.py:40` rebuilds from persisted body fields but does not compare the stored `hash` column.
- `services/api/verge_api/routes/ops.py:41` correctly says a trusted `expectedHead` is required for proof of authenticity.
- Evidence manifests upload to object storage, but no object-lock/WORM retention is configured in deploy manifests.

Risk: the current chain catches accidental/local tampering, but a database actor can re-forge a fully consistent chain unless heads are anchored out of band. Evidence packs can also be overwritten/deleted unless object storage retention is enforced.

Target state:

- Store and verify signed audit heads externally: offline plant ledger, HSM/KMS-backed signatures, transparency log, or write-once medium.
- Compare persisted hash values during reload, enforce append-only writes at DB level, and forbid delete/update on audit tables for app roles.
- Enable MinIO/S3 Object Lock WORM retention for evidence buckets.
- Sign evidence manifests and release bundles; attach SBOM/provenance attestations to container images.

Comparable systems: MinIO object lock provides WORM retention; Sigstore/Cosign signs containers and attestations; OpenLineage provides a standard event model for lineage metadata.

### 4. Persistence Is Durable Enough for Demo, Not Yet Operationally Safe

Evidence:

- `services/api/verge_api/db.py:100` calls `metadata.create_all()` at runtime.
- `services/api/verge_api/db.py:42-47` feedback has no foreign key to finding.
- `services/api/verge_api/db.py:52-63` audit has no DB-level append-only constraints beyond application behavior.
- `services/api/verge_api/sql_store.py:52` implements idempotency as delete-then-insert.
- `services/api/verge_api/routes/readings.py:31` writes to Timescale but ignores the return value.
- `services/api/verge_api/timescale_writer.py:4` describes Timescale writes as best-effort and non-blocking.

Risk: finding and audit writes are not atomic as a business event; silent Timescale failures make incident reconstruction incomplete; runtime DDL is risky for production; delete-then-insert can create races and changes audit semantics.

Target state:

- Promote Alembic to mandatory migrations in all non-test deployments.
- Add foreign keys, check constraints, unique constraints, indexes, and retention/partition policy.
- Replace delete-then-insert with dialect-aware upsert and immutable event tables.
- Add outbox pattern: write finding/audit/stream notification in one transaction, publish after commit.
- Treat Timescale as canonical telemetry storage for historical charts; keep in-memory buffers only as caches.

### 5. Kubernetes/Runtime Manifests Are Not Production Hardened

Evidence:

- `deploy/k8s/api-deployment.yaml:7` and `risk-engine-deployment.yaml:7` run single replicas.
- `deploy/k8s/api-deployment.yaml:18` and `risk-engine-deployment.yaml:18` use `:latest`.
- K8s manifests lack resource requests/limits, security contexts, NetworkPolicies, PodDisruptionBudgets, Secrets, autoscaling, ingress/TLS, service accounts, and backup/restore jobs.
- `deploy/docker-compose.yml` intentionally uses dev passwords and dev modes.

Risk: no scheduling guarantees, no blast-radius control, weak rollout/rollback, weak supply-chain traceability, and no operational posture for a plant DMZ.

Target state:

- Pin images by version/digest, sign images, publish SBOMs.
- Add resources, non-root `securityContext`, read-only filesystems where possible, service accounts, and restricted Pod Security settings.
- Add PDB/HPA where horizontally safe; keep risk-engine single-writer until stream state is partition-safe.
- Add NetworkPolicies and TLS.
- Add backup, restore, and disaster recovery runbooks with automated restore drills.

Comparable systems: Kubernetes docs call out probes, resource requests/limits, NetworkPolicies, and PodDisruptionBudgets as first-class production primitives.

### 6. Data Contracts Exist But Are Not a Registry or Enforced Boundary

Evidence:

- `packages/contracts/verge_contracts/contracts.py` provides in-process validation.
- `services/api/verge_api/routes/readings.py:26` accepts readings without invoking the contract registry.
- `services/risk-engine/verge_risk/runner.py:47` assumes event fields exist.

Risk: contracts can pass unit tests while live producers still bypass them. Schema evolution is local Python code, not centrally governed compatibility.

Target state:

- Add a real schema registry for event contracts or a deployable local equivalent for air-gapped sites.
- Enforce validation at every producer boundary: edge, replay, connector, API ingest, Redpanda producer.
- Add CI compatibility checks for every schema change and versioned AsyncAPI docs.

Comparable systems: Apicurio and Confluent Schema Registry enforce validity and compatibility rules to control schema evolution.

### 7. MLOps Is a Registry View, Not a Production ML Lifecycle

Evidence:

- `services/risk-engine/verge_risk/ml_layer.py:55` trains a synthetic demo IsolationForest at runtime.
- `services/risk-engine/verge_risk/ml_layer.py:95` pads/truncates features to fit a demo vector.
- `packages/mlops/verge_mlops/registry.py` tracks stages and metrics but does not serve artifacts or drive scoring.

Risk: model promotion and model use are disconnected. The registry can say production while scoring still uses an in-code synthetic model.

Target state:

- Load model artifacts by registry reference and verify artifact digest/signature.
- Store feature definitions, training data lineage, validation metrics, calibration, thresholds, and rollback criteria.
- Add shadow/canary measurement loops tied to operator feedback.
- Use MLflow-compatible registry semantics and KServe/Triton-like serving where model complexity grows.

Comparable systems: MLflow Model Registry tracks registered models, versions, aliases, tags, and metadata; KServe supports canary rollout strategies for inference services.

### 8. Edge and Enterprise Connectors Are Honest But Still Thin

Evidence:

- CSV historian and CMMS connectors are real.
- Network PI/PHD/Maximo/SAP/Milestone connectors currently degrade with "configured but unreachable" (`services/connectors/verge_connectors/historian.py:114`, `cmms.py:110`).
- `services/edge-gateway/verge_edge/forward.py` forwards directly to API, not through a durable local spool.

Risk: the real hard work in industrial deployments is connector certification, credential handling, retries, store-and-forward, timestamp normalization, and failure observability.

Target state:

- Define connector SDK: `pull`, `checkpoint`, `ack`, `health`, `metrics`, `capabilities`, `sample`, `contract_validate`.
- Add local durable spool on edge gateways.
- Add per-connector integration tests using recorded fixtures and vendor sandboxes.
- Separate device services, normalization/app services, and rules/analytics boundaries.

Comparable systems: EdgeX Foundry separates device ingestion, message bus, app services, security, management, and rules/local analytics.

### 9. Compliance Is Deterministic But Too Heuristic For Legal Use

Evidence:

- `services/compliance/verge_compliance/gaps.py` determines many controls by rule-name text or simple predicate presence.
- Clause packs are code/data in repo, not signed, versioned regulatory artifacts.

Risk: a legal/compliance report can overstate coverage if a rule exists by name but is not calibrated, enabled, tested, or mapped to the correct plant asset.

Target state:

- Version and sign compliance packs.
- Map every clause to required evidence types, plant-specific configuration, rule test cases, commissioning artifacts, and runtime proof.
- Consider OPA/Rego for policy-as-code where requirements are JSON facts + formal policy.
- Add a report disclaimer level: `platform-provided`, `configured`, `observed`, `operator-attested`, `not-evidenced`.

Comparable systems: OPA provides policy-as-code and APIs for externalized decision-making.

### 10. Observability Is Useful But Not End-to-End

Evidence:

- `/metrics` exists and tests pass.
- `deploy/otel-collector-config.yaml` exists.
- Trace middleware exists, but the risk engine, edge, connectors, Redpanda publish/consume, DB writes, and object store writes are not all joined into distributed traces.

Risk: during a plant incident, "why did this finding not appear?" must be answerable across edge input, broker offset, risk evaluation, DB write, notification, and operator action.

Target state:

- Propagate `trace_id`, `event_id`, `site_id`, `source_id`, and `schema_version`.
- Emit metrics for ingest lag, connector skips, DLQ size, rule firings, dedupe suppressions, forecast quality, audit append latency, DB transaction failure, object-store write failure.
- Add structured logs and dashboards with SLOs.

Comparable systems: OpenTelemetry standardizes traces, metrics, and logs collection/export through a vendor-neutral framework.

## Module-by-Module Modernization Map

| Module | Current state | Production reference | Upgrade direction |
| --- | --- | --- | --- |
| Edge gateway/connectors | Good normalizer, CSV connectors, degraded network stubs | EdgeX Foundry / Fledge-style edge services | Durable spool, connector SDK, health/metrics, cert auth, per-vendor integration packs |
| Event bus/streaming | Redpanda present, Python consumer, in-memory CEP/dedupe | Kafka/Redpanda + Flink CEP | Event IDs, schema registry, DLQ, offset discipline, event-time state |
| Risk engine | Deterministic rules, lineage, forecast, health down-weight | Rules library inside stateful stream processor | Partition-safe state, event-time windows, explainable rule versions |
| Data contracts | In-process Python registry | Apicurio/Confluent Schema Registry | Central compatibility, producer enforcement, AsyncAPI |
| Source lineage | Finding lineage strings | OpenLineage facets/events | Standard lineage events across edge, risk, model, reports |
| Persistence | Postgres JSON source-of-truth + Timescale best-effort | Event/outbox + relational constraints + hypertables | Migration gates, transactions, canonical telemetry history |
| Audit/evidence | Hash chain + optional snapshot head | WORM object lock + signatures/transparency | Signed anchored heads, WORM evidence, app role append-only |
| MLOps | JSON registry + synthetic runtime model | MLflow + KServe/Triton | Artifact loading, signed models, drift gates, canary routing |
| Compliance | Deterministic heuristic gap detector | Policy-as-code + signed clause packs | Evidence requirements, OPA/Rego, signed pack versions |
| Deployment | Compose + starter K8s | Hardened Kubernetes | Secrets, resources, NetworkPolicy, PDB/HPA, signed images |
| Observability | `/metrics`, OTel collector | OTel + Prometheus/Grafana/Loki/Tempo | Trace propagation and SLO dashboards |
| OT security | Keycloak optional | NIST 800-82 OT security posture | Segmentation, least privilege, secure remote access, asset inventory |

## Ready-To-Deploy Target Architecture

1. Edge: protocol adapters collect OPC-UA/MQTT/CSV/VMS data into a local durable spool, validate against contracts, sign event batches, and publish to Redpanda when the DMZ link is available.
2. Event plane: Redpanda topics are schema-registered, partitioned by site/zone/sensor, monitored for lag, and protected with TLS/SASL/mTLS.
3. Risk plane: deterministic rules run inside a partition-safe event-time processor. Pilot can stay Python if it adds durable state and offset discipline; advanced deployment should evaluate Flink CEP for temporal joins and late-event semantics.
4. API/control plane: FastAPI remains the gateway, but all mutating routes require RBAC, object-level authorization, idempotency keys, and audit attribution from token identity.
5. Data plane: Postgres/PostGIS holds configuration, permits, lifecycle, audit metadata; Timescale holds telemetry; MinIO WORM holds evidence; Neo4j/PostGIS graph is synchronized from commissioned plant source-of-truth.
6. Audit plane: every decision/action/evidence pack appends to DB and object store, signs the audit head, and periodically anchors it outside the mutable database.
7. Ops plane: OTel traces and Prometheus metrics answer event-path questions end-to-end; backup/restore and incident replay are routine automated checks.

## Suggested 90-Day Hardening Plan

### First 30 Days: Close Production-Blocking Gaps

- Turn auth on by default for cluster deployment; add JWT audience validation and route RBAC.
- Replace K8s ConfigMap secrets/demo passwords with `Secret`; disable demo users in non-dev.
- Add event IDs, idempotency keys, schema version, and site ID to canonical events.
- Enforce contract validation at API ingest, edge forward, replay, and risk consumer.
- Add migration-based DB boot for SQL mode and stop using runtime `create_all` outside tests.
- Add DLQ/retry topics and consumer lag metrics.

### Days 31-60: Make Reliability Measurable

- Implement outbox pattern for finding/audit/notify.
- Persist risk dedupe state and permit validity state across restart.
- Move telemetry history reads to Timescale with in-memory cache fallback.
- Add signed audit-head anchoring and WORM object lock for evidence.
- Add Kubernetes resources/securityContext/NetworkPolicies/PDBs and image tags/digests.
- Add OTel traces from edge -> broker -> risk -> API -> DB/object store.

### Days 61-90: Move From Pilot To Product

- Evaluate Flink CEP or equivalent for compound temporal correlation at scale.
- Add connector certification harness and vendor sandbox fixtures.
- Connect MLOps registry to actual artifact loading, shadow/canary metrics, drift gates, and rollback.
- Convert compliance packs to signed versioned artifacts with explicit evidence requirements.
- Add backup/restore drills, chaos/network-partition drills, and incident replay as CI artifacts.

## Sources Consulted

- Apache Flink: event time/watermarks and CEP: https://nightlies.apache.org/flink/flink-docs-stable/docs/concepts/time/ and https://nightlies.apache.org/flink/flink-docs-stable/docs/libs/cep/
- Apache Kafka documentation: https://kafka.apache.org/documentation/
- EdgeX Foundry: https://lfedge.org/projects/edgex-foundry/
- NIST SP 800-82 Rev. 3, Guide to Operational Technology Security: https://csrc.nist.gov/pubs/sp/800/82/r3/final
- OpenTelemetry docs: https://opentelemetry.io/docs/
- MLflow Model Registry: https://mlflow.org/docs/latest/ml/model-registry/
- KServe canary rollout: https://kserve.github.io/website/docs/model-serving/predictive-inference/rollout-strategies/canary
- Apicurio Registry rules/compatibility: https://www.apicur.io/registry/docs/apicurio-registry/3.3.x/getting-started/assembly-intro-to-registry-rules.html
- OpenLineage: https://openlineage.io/docs/
- MinIO object locking/WORM: https://docs.min.io/aistor/administration/object-locking-and-immutability/
- Kubernetes probes/resources/network policies/PDBs: https://kubernetes.io/docs/
- Keycloak Authorization Services: https://www.keycloak.org/docs/latest/authorization_services/
- OWASP API Security Top 10 2023: https://owasp.org/www-project-api-security/
- Sigstore/Cosign: https://docs.sigstore.dev/cosign/
- Open Policy Agent: https://openpolicyagent.org/docs/
