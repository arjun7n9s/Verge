import { request } from './client';

export interface PermitWire {
  permitId: string;
  kind: string;
  zoneId: string;
  equipmentId?: string | null;
  validFrom: string;
  validTo: string;
  status: string;
}

export interface PermitConflict {
  permitA: string;
  permitB: string;
  zones: string[];
  reason: string;
  severity: string;
}

export async function getPermits(signal?: AbortSignal): Promise<PermitWire[]> {
  return request<PermitWire[]>('/api/permits', { signal });
}

export async function getPermitConflicts(signal?: AbortSignal): Promise<{
  conflicts: PermitConflict[];
  count: number;
}> {
  return request('/api/permits/conflicts', { signal });
}

export interface ShiftHandoverReport {
  markdown: string;
  openFindings: string[];
  submitted: boolean;
  narrativeDegraded: boolean;
}

export async function draftShiftHandoverReport(
  notes: string,
  actor = 'maya',
  transcript?: string,
): Promise<ShiftHandoverReport> {
  return request<ShiftHandoverReport>('/api/reports/shift-handover', {
    method: 'POST',
    body: { actor, notes, transcript },
  });
}
