import { request } from './client';

export interface AuditEntryWire {
  entryId: string;
  timestamp: string;
  actor: string;
  kind: string;
  payload: Record<string, unknown>;
  prevHash: string;
  hash: string;
}

export async function getAuditEntries(limit = 50, signal?: AbortSignal): Promise<AuditEntryWire[]> {
  return request<AuditEntryWire[]>(`/api/audit?limit=${limit}`, { signal });
}
