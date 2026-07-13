import { request } from './client';

/* Worker location plane (omlox-style zone presence). Zone-level only —
   precise coordinates stay in the RTLS hub; the console shows who is in
   which zone and how fresh the fix is. */

export interface WorkerPosition {
  workerId: string;
  zoneId: string;
  ts: string;
  name: string;
  role: string;
  source: string;
  ageS: number;
  stale: boolean;
}

export interface WorkersSnapshot {
  workers: WorkerPosition[];
  byZone: Record<string, WorkerPosition[]>;
  total: number;
  stale: number;
  latestFixTs: string | null;
}

export interface FindingExposure {
  findingId: string;
  zones: string[];
  adjacentZones: string[];
  inZone: WorkerPosition[];
  inAdjacent: WorkerPosition[];
  headcountAtRisk: number;
  staleFixes: number;
}

export async function listWorkers(signal?: AbortSignal): Promise<WorkersSnapshot> {
  return request<WorkersSnapshot>('/api/workers', { signal });
}

export async function getFindingExposure(
  findingId: string,
  signal?: AbortSignal,
): Promise<FindingExposure> {
  return request<FindingExposure>(
    `/api/findings/${encodeURIComponent(findingId)}/exposure`,
    { signal },
  );
}
