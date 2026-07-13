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
  timescale?: { configured: boolean; degraded: boolean; readings?: number; reason?: string };
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

export interface ComplianceClause {
  clauseId: string;
  oisdRef: string;
  standard: string;
  title: string;
  requirement: string;
  capability: string;
  isPlatform: boolean;
  status: 'satisfied' | 'gap';
  reason: string;
}

export interface ComplianceReport {
  plant: string;
  coverageRatio: number;
  satisfied: number;
  gaps: number;
  total: number;
  clauses: ComplianceClause[];
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

export interface CorrectiveAction {
  actionId: string;
  source: string;
  title: string;
  requirement: string;
  controlTier: string;
  state: 'open' | 'in-progress' | 'pending-verification' | 'closed-effective' | 'reopened';
  clauseId: string | null;
  findingId: string | null;
  standard: string | null;
  owner: string | null;
  due: string | null;
  createdAt: string;
  history: { from: string; to: string; actor: string; note: string; ts: string }[];
}

export async function listCorrectiveActions(
  signal?: AbortSignal,
): Promise<{ actions: CorrectiveAction[]; total: number; openCount: number }> {
  return request('/api/compliance/actions', { signal });
}

export async function generateCorrectiveActions(): Promise<{
  created: CorrectiveAction[];
  count: number;
  note: string | null;
}> {
  return request('/api/compliance/actions/generate', { method: 'POST' });
}

export async function transitionCorrectiveAction(
  actionId: string,
  to: string,
  actor: string,
  note?: string,
): Promise<CorrectiveAction> {
  return request(`/api/compliance/actions/${encodeURIComponent(actionId)}/transition`, {
    method: 'POST',
    body: JSON.stringify({ to, actor, note }),
  });
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

export async function getEvalReport(signal?: AbortSignal): Promise<unknown[]> {
  return request<unknown[]>('/api/eval/report', { signal });
}

export interface StreamStatus {
  subscribers: number;
  redpandaFanout: boolean;
  fanoutConfigured: boolean;
}

export async function getStreamStatus(signal?: AbortSignal): Promise<StreamStatus> {
  return request<StreamStatus>('/api/stream/status', { signal });
}

export async function syncPlantGraph(signal?: AbortSignal): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>('/api/plant/graph-sync', { method: 'POST', signal });
}

export interface TimescaleStatus {
  configured: boolean;
  degraded: boolean;
  readings?: number;
  reason?: string;
}

export async function getTimescaleStatus(signal?: AbortSignal): Promise<TimescaleStatus> {
  return request<TimescaleStatus>('/api/timescale/status', { signal });
}

export interface FatigueZoneMetric {
  zoneId: string;
  current: number;
  limit: number;
  pct: number;
}

export interface FatigueMetrics {
  fpr: number | null;
  alertsPerShift: number;
  falseAlarmRatio: number | null;
  operatorActionRate: number | null;
  trend: Array<{ date: string; falseAlarms: number; useful: number }>;
  zones: FatigueZoneMetric[];
  measured: boolean;
}

export async function getFatigueMetrics(signal?: AbortSignal): Promise<FatigueMetrics> {
  return request<FatigueMetrics>('/api/fatigue/metrics', { signal });
}

export interface PlumeExclusionFeature {
  type: 'Feature';
  properties: Record<string, unknown>;
  geometry: { type: 'Polygon'; coordinates: number[][][] };
}

export interface ZoneExclusion {
  zoneId: string;
  exclusion: PlumeExclusionFeature;
}

export async function getZoneExclusion(
  zoneId: string,
  params?: { windSpeedMs?: number; windDirDeg?: number; releaseRateKgS?: number },
  signal?: AbortSignal,
): Promise<ZoneExclusion> {
  const qs = new URLSearchParams();
  if (params?.windSpeedMs != null) qs.set('windSpeedMs', String(params.windSpeedMs));
  if (params?.windDirDeg != null) qs.set('windDirDeg', String(params.windDirDeg));
  if (params?.releaseRateKgS != null) qs.set('releaseRateKgS', String(params.releaseRateKgS));
  const q = qs.toString();
  return request<ZoneExclusion>(
    `/api/zones/${encodeURIComponent(zoneId)}/exclusion${q ? `?${q}` : ''}`,
    { signal },
  );
}
