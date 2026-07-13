import { request } from './client';
import type { WorkerPosition } from './workers';

/* Emergency mode (spec §4.4): declare → evidence freeze + evacuation plan +
   muster roll-call → stand down. All operator-gated (P8), all audit-chained. */

export interface ZoneRoute {
  zoneId: string;
  musterId: string | null;
  musterZone: string | null;
  route: string[];
  hops: number;
  trapped: boolean;
}

export interface EvacuationPlan {
  affectedZones: string[];
  usableMusterPoints: { musterId: string; zoneId: string; name: string }[];
  unusableMusterPoints: string[];
  routes: Record<string, ZoneRoute>;
  trappedZones: string[];
}

export interface MusterCheckIn {
  workerId: string;
  musterId: string;
  recordedBy: string;
  ts: string;
}

export interface MissingWorker {
  workerId: string;
  name: string;
  role: string;
  lastKnownZone: string;
  lastFixTs: string;
  lastFixStale: boolean;
}

export interface EmergencyStatus {
  active: boolean;
  emergencyId?: string;
  findingId?: string;
  declaredAt?: string;
  declaredBy?: string;
  affectedZones?: string[];
  evacuation?: EvacuationPlan;
  muster?: {
    expected: number;
    accounted: MusterCheckIn[];
    missing: MissingWorker[];
    allAccounted: boolean;
  };
  evidenceFreeze?: {
    hash: string;
    frozenAt: string;
    telemetrySeries: number;
    rosterSize: number;
  };
  stoodDownAt?: string;
  stoodDownBy?: string;
}

export async function getEmergencyStatus(signal?: AbortSignal): Promise<EmergencyStatus> {
  return request<EmergencyStatus>('/api/emergency/status', { signal });
}

export async function declareEmergency(
  findingId: string,
  approvedBy: string,
): Promise<EmergencyStatus> {
  return request<EmergencyStatus>(
    `/api/findings/${encodeURIComponent(findingId)}/emergency/declare`,
    { method: 'POST', body: JSON.stringify({ approvedBy }) },
  );
}

export async function musterCheckIn(
  workerId: string,
  musterId: string,
  recordedBy: string,
): Promise<EmergencyStatus> {
  return request<EmergencyStatus>('/api/emergency/muster/check-in', {
    method: 'POST',
    body: JSON.stringify({ workerId, musterId, recordedBy }),
  });
}

export async function emergencyStandDown(approvedBy: string): Promise<EmergencyStatus> {
  return request<EmergencyStatus>('/api/emergency/stand-down', {
    method: 'POST',
    body: JSON.stringify({ approvedBy }),
  });
}

export type { WorkerPosition };
