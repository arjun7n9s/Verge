import { request } from './client';

export interface PlantSensor {
  sensorId: string;
  kind: string;
  zoneId: string;
  threshold?: number | null;
}

export interface PlantGeoJson {
  type: 'FeatureCollection';
  properties: { plant: string };
  features: Array<{
    type: 'Feature';
    properties: { zoneId: string; name: string; adjacent?: string[] };
    geometry: { type: 'Polygon'; coordinates: number[][][] };
  }>;
  sensors: PlantSensor[];
}

export async function getPlantGeoJson(signal?: AbortSignal): Promise<PlantGeoJson> {
  return request<PlantGeoJson>('/api/plant/geojson', { signal });
}
