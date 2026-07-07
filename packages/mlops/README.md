# verge-mlops

Model registry + drift detection for the ML layer (spec §14 Phase 4). The safety
path is rules + classic ML; this gives that ML layer the same discipline as the
finding lifecycle — nothing reaches production without shadow + canary first —
and an early-warning when its world drifts. Dependency-free and file-backed, so
it version-controls and ships inside an air-gapped bundle (P2).

## Registry lifecycle

```
registered → shadow → canary → production → retired
                  ↘ retired   ↘ shadow / retired
```

Promotion is an explicit, recorded transition; illegal jumps raise. Exactly one
model per name is in `production` — promoting a replacement retires the incumbent.

```python
from verge_mlops import ModelRegistry, ModelCard, SHADOW, CANARY, PRODUCTION

reg = ModelRegistry("registry.json")          # file-backed; omit path for in-memory
reg.register(ModelCard("cr-1.3.0", "compound-risk", "1.3.0", "isolation-forest"))
reg.promote("cr-1.3.0", SHADOW)
reg.promote("cr-1.3.0", CANARY)
reg.promote("cr-1.3.0", PRODUCTION)            # retires the previous production
reg.production("compound-risk")                # -> the live ModelCard
```

## Drift (Population Stability Index)

```python
from verge_mlops import population_stability_index

r = population_stability_index(reference_scores, live_scores)
r.psi, r.severity, r.drifted     # e.g. 0.31, "significant", True
```

Bands: `< 0.10` stable · `0.10–0.25` moderate · `≥ 0.25` significant (retrain).

## Router (canary rollout)

```python
from verge_mlops import ModelRouter

router = ModelRouter(reg, canary_zones={"compound-risk": {"B-04"}})
router.route("compound-risk", zone="B-04").stage   # "canary"
router.route("compound-risk", zone="B-01").stage   # "production"
router.route("unknown").routed                       # False -> caller falls back to rules
```

Default is production; a canary is served only to its configured zones. No model
⇒ `routed=False` — the safety path falls back to rules (P1), never a guess.

## Surfaces

- CLI: `verge models` (lists the registry; `--registry PATH`, `--json`).
- API: `GET /api/models` (summary + cards; `?stage=`), and the registry rollup
  appears in `GET /api/ops/status` + `/metrics` (`verge_models_total`).
- Env: `VERGE_MODEL_REGISTRY=/path/to/registry.json` (else the bundled demo).
