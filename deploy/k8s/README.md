# Verge — K3s / production OT-DMZ profile (spec §8, §14.6)

Minimal manifests for air-gapped pilot installs. Pair with signed bundles
(`verge upgrade`) and external Postgres/Redpanda/MinIO as required by the plant.

## Layout

| Manifest | Purpose |
|----------|---------|
| `namespace.yaml` | `verge` namespace |
| `configmap.yaml` | Non-secret env (site id, broker URLs) |
| `api-deployment.yaml` | FastAPI gateway + probes on `/health` |
| `api-service.yaml` | ClusterIP :8000 |
| `console-deployment.yaml` | nginx static console |
| `console-service.yaml` | ClusterIP :80 |
| `risk-engine-deployment.yaml` | Redpanda consumer → API |

## Apply (pilot)

```bash
kubectl apply -f deploy/k8s/namespace.yaml
kubectl apply -f deploy/k8s/configmap.yaml
# Create secrets separately (POSTGRES_PASSWORD, API keys) — never commit secrets.
kubectl apply -f deploy/k8s/
```

Scrape `/metrics` from the API Service via Prometheus Operator or plant-IT
Prometheus — see `deploy/observability/`.

## Notes

- Swap `VERGE_LLM_PROVIDER` to `ollama` / `vllm` for on-prem inference.
- Enable `VERGE_AUTH_ENABLED=true` when Keycloak is reachable from the cluster.
- Run `alembic upgrade head` as a Job before first API rollout when using SQL store.
