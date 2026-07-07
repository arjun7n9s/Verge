# Commissioning workflow (spec §14.5)

> How a plant goes live — and the sales conversation: *"Before you install
> anything, here's what Verge would have caught in your plant's last 6 months."*

Every pilot plant follows six steps, in order. The replay engine (§10) does
double duty as the commissioning validator. Verge **acts on nothing** here (P8);
it reports readiness so the safety officer decides go-live with **measured
numbers, not a pitch**.

The whole workflow runs from the `verge` CLI with **no external dependencies**
— the layout geometry is validated by a self-contained toolkit
(`verge_twin.geometry`), so it runs on an air-gapped OT box with no GEOS/shapely
install (P2 sovereign-by-default).

## One command

```bash
# Full 6-step dry run on the bundled Vizag demo plant:
verge commission

# A real plant:
verge commission \
  --name acme-refinery \
  --layout acme-zones.geojson \
  --sensors acme-sensors.csv \
  --out acme-commissioning.md
```

Exit code is `0` when the plant is **ready for 30-day shadow mode**, non-zero
when a step needs attention. `--json` emits the machine-readable report.

## The six steps

| Step | CLI | What it proves |
|------|-----|----------------|
| 1 · Import plant layout | `verge plant import --file zones.geojson --name P` | Zones don't **overlap**; adjacency is **inferred** from shared boundaries (feeds SIMOPS); coverage is reported so **gaps** are visible. |
| 2 · Map sensors to zones | `verge sensor map --csv sensors.csv --layout zones.geojson` | Every sensor lands in a zone by explicit `zone` or by `lon/lat`. Unmapped sensors are flagged **`unassigned`** and excluded from scoring. |
| 3 · Adopt the rule library | `verge rules adopt --library oisd-starter` | The plant starts from **known fatal combinations**, not a blank page. Customize per zone/shift before go-live. |
| 4 · Set thresholds | (from the mapped sensors + Rules DSL) | Every sensor kind in scope has a threshold. |
| 5 · Dry-run against history | `verge replay --incident <id>` (folded into `commission`) | **The persuasive artifact** — what Verge would have caught, the lead time, and the band, vs. the B0/B1/B2 baselines. |
| 6 · Shadow mode (30 days) | engine `--shadow` | The mandatory, default-on, no-opt-out next step. Day 31: review with the safety officer using real `FindingFeedback`. |

## Individual steps

```bash
# Step 1 — validate a layout and (optionally) write the commissioned plant YAML:
verge plant import --file zones.geojson --name acme --sensors sensors.csv --out acme.yaml

# Step 2 — inspect the sensor mapping (unassigned sensors are called out):
verge sensor map --csv sensors.csv --layout zones.geojson --json

# Step 3 — adopt the starter rule library:
verge rules adopt
```

## Input formats

**Zone GeoJSON** — a `FeatureCollection`; each feature needs a `zoneId` (or
`id`) property and a `Polygon` geometry:

```json
{ "type": "Feature",
  "properties": { "zoneId": "B-04", "name": "Coke-oven battery 4" },
  "geometry": { "type": "Polygon", "coordinates": [[[...]]] } }
```

**Sensor CSV** — `sensorId,kind,unit,zone,lon,lat,threshold,cadenceS`. A sensor
is placed by explicit `zone` if given, else by `lon/lat` point-in-zone. Leave
both blank to see it reported as `unassigned`.

Bundled demo inputs live in `services/twin/verge_twin/plants/`
(`vizag-zones.geojson`, `vizag-sensors.csv`).

## Why this matters for Horizon 1

Horizon 0 exit criterion #4 is *"shadow-mode commissioning is built and ready —
the next plant can use it day 1 of Horizon 1."* This workflow **is** that: the
same replay harness that grades Verge in CI is the tool a plant runs against its
own history before a single sensor is wired live.
