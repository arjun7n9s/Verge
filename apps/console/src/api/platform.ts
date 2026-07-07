import { request } from './client';

export interface DegradationBanner {
  code: string;
  severity: 'info' | 'warn' | 'critical';
  message: string;
}

export interface DegradationStatus {
  banners: DegradationBanner[];
  count: number;
}

export interface OpsStatus {
  version: string;
  uptimeSeconds: number;
  audit: { entries: number; head: string; verified: boolean };
  findings: { total: number };
  sensorHealth: { counts: Record<string, number>; total: number; livePct: number | null };
  ingest: { sensors: number; readings: number; lastReadingTs: string | null };
  llm: { provider: string; degraded: boolean };
  vision: { backend: string; degraded: boolean; reason?: string };
  modelRegistry: Record<string, unknown>;
  backup: { lastTs: string | null; ageSeconds: number | null };
  signedBundle: { builtTs: string | null; ageSeconds: number | null };
  lastReplayRun: { ts: string | null; ageSeconds: number | null };
}

export interface ComplianceGap {
  clauseId: string;
  standard: string;
  title: string;
  severity: string;
  status: string;
}

export interface ComplianceGaps {
  plant: string;
  gaps: ComplianceGap[];
}

export interface ComplianceReport extends ComplianceGaps {
  coverageRatio: number;
  evidencePack?: Record<string, unknown>;
}

export interface ModelCard {
  name: string;
  version: string;
  stage: string;
  metrics?: Record<string, number>;
}

export interface ModelRegistry {
  summary: Record<string, unknown>;
  models: ModelCard[];
}

export interface AlertDispatchReceipt {
  alertId: string;
  findingId: string;
  approvedBy?: string | null;
  refused: boolean;
  reason?: string;
  anyDelivered?: boolean;
  results: Array<{ channel: string; delivered: boolean; degraded: boolean; reason?: string }>;
}

export interface CommissionCheck {
  step: string;
  status: string;
  detail: string;
}

export interface CommissionSummary {
  plant: string;
  ready: boolean;
  checks: CommissionCheck[];
  dryRun?: Array<Record<string, unknown>>;
}

export async function getCommissionSummary(signal?: AbortSignal): Promise<CommissionSummary> {
  return request<CommissionSummary>('/api/commission/summary', { signal });
}

export async function getIncidentReport(
  findingId: string,
  signal?: AbortSignal,
): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/api/findings/${findingId}/incident-report`, {
    signal,
  });
}

export async function getDegradationStatus(signal?: AbortSignal): Promise<DegradationStatus> {
  return request<DegradationStatus>('/api/degradation', { signal });
}

export async function getOpsStatus(signal?: AbortSignal): Promise<OpsStatus> {
  return request<OpsStatus>('/api/ops/status', { signal });
}

export async function getComplianceGaps(signal?: AbortSignal): Promise<ComplianceGaps> {
  return request<ComplianceGaps>('/api/compliance/gaps', { signal });
}

export async function getComplianceReport(signal?: AbortSignal): Promise<ComplianceReport> {
  return request<ComplianceReport>('/api/compliance/report', { signal });
}

export async function getModelRegistry(signal?: AbortSignal): Promise<ModelRegistry> {
  return request<ModelRegistry>('/api/models', { signal });
}

export async function dispatchAlert(
  findingId: string,
  body: {
    approvedBy: string;
    channels?: string[];
    action?: string;
    languages?: string[];
  },
  signal?: AbortSignal,
): Promise<AlertDispatchReceipt> {
  return request<AlertDispatchReceipt>(`/api/findings/${findingId}/alert/dispatch`, {
    method: 'POST',
    body,
    signal,
  });
}
