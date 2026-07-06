import type { LeadTimeBand, RiskFinding } from '@/types';
import type { PlantGeoJson } from '@/api/plant';

const BAND_TO_ALERT: Record<LeadTimeBand, string> = {
  IMMINENT: 'imminent',
  NEAR: 'near',
  WATCH: 'watch',
  UNKNOWN: 'none',
};

const BAND_RANK: Record<string, number> = { imminent: 3, near: 2, watch: 1, none: 0 };

export function polygonCentroid(ring: number[][]): [number, number] {
  const pts = ring.slice(0, -1);
  const n = pts.length || 1;
  const lng = pts.reduce((s, [x]) => s + x, 0) / n;
  const lat = pts.reduce((s, [, y]) => s + y, 0) / n;
  return [lng, lat];
}

export function zoneAlertStates(findings: RiskFinding[]): Record<string, string> {
  const out: Record<string, number> = {};
  for (const f of findings) {
    if (f.shadow) continue;
    const alert = BAND_TO_ALERT[f.leadTimeBand] ?? 'none';
    const rank = BAND_RANK[alert] ?? 0;
    out[f.zoneId] = Math.max(out[f.zoneId] ?? 0, rank);
  }
  const rankToAlert = Object.fromEntries(
    Object.entries(BAND_RANK).map(([k, v]) => [v, k]),
  );
  return Object.fromEntries(
    Object.entries(out).map(([zone, rank]) => [zone, rankToAlert[rank] ?? 'none']),
  );
}

export function enrichPlantGeoJson(plant: PlantGeoJson, findings: RiskFinding[]) {
  const alerts = zoneAlertStates(findings);
  const features = plant.features.map((feat) => ({
    ...feat,
    properties: {
      ...feat.properties,
      alertState: alerts[feat.properties.zoneId] ?? 'none',
    },
  }));
  return { ...plant, features };
}

export function sensorsWithCoords(
  plant: PlantGeoJson,
  zoneCentroids: Record<string, [number, number]>,
) {
  return plant.sensors.map((s) => ({
    id: s.sensorId,
    name: `${s.kind} · ${s.zoneId}`,
    coordinates: zoneCentroids[s.zoneId] ?? [0, 0],
    status: 'live' as const,
    value: s.threshold != null ? `thr ${s.threshold}` : '—',
  }));
}

export function centroidsByZone(plant: PlantGeoJson): Record<string, [number, number]> {
  const out: Record<string, [number, number]> = {};
  for (const feat of plant.features) {
    const ring = feat.geometry.coordinates[0];
    out[feat.properties.zoneId] = polygonCentroid(ring);
  }
  return out;
}
