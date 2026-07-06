# verge-memory

Cognee-backed memory context for Verge findings.

The package is degraded-by-default: if `VERGE_COGNEE_ENABLED=true`,
`COGNEE_API_KEY`, and a Cognee tenant URL are not configured, retrieval returns
empty context with `degraded: true` instead of raising into the API.

## Environment

```bash
VERGE_COGNEE_ENABLED=true
COGNEE_API_KEY=...
COGNEE_BASE_URL=https://your-tenant.aws.cognee.ai
VERGE_SITE_ID=vizag-demo
COGNEE_DATASET_PREFIX=verge
```

`COGNEE_SERVICE_URL` is also accepted for self-hosted Cognee.

## API Shape

`context_for_finding(finding)` returns:

```json
{
  "findingId": "F-CONV-07",
  "similarIncidents": [],
  "regulatoryClauses": [],
  "plantHistory": [],
  "degraded": true
}
```

When Cognee is configured, the first retrieve call idempotently ingests the
static seed corpus, cognifies the dataset, then queries it.

## Free-Text Query

`query_memory("what should the operator check?", finding=finding)` returns:

```json
{
  "answer": "",
  "citations": [],
  "degraded": true
}
```

API route:

```bash
curl -X POST http://localhost:8000/api/memory/query \
  -H "Content-Type: application/json" \
  -d '{"query":"what clauses apply?","findingId":"F-CONV-07"}'
```
