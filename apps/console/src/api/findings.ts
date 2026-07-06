import type { RiskFinding, FindingState, FeedbackVerdict } from '@/types';
import { request } from './client';

const ACTOR = 'maya';

export async function getFindings(shadow = false, signal?: AbortSignal): Promise<RiskFinding[]> {
  return request<RiskFinding[]>(`/api/findings?shadow=${shadow}`, { signal });
}

export async function getFinding(id: string, signal?: AbortSignal): Promise<RiskFinding> {
  return request<RiskFinding>(`/api/findings/${id}`, { signal });
}

export async function transitionFinding(
  id: string,
  to: FindingState,
  reasonText?: string,
  reasonCode?: string,
  actor = ACTOR,
): Promise<RiskFinding> {
  return request<RiskFinding>(`/api/findings/${id}/transition`, {
    method: 'POST',
    body: { to, actor, reasonText, reasonCode },
  });
}

export async function submitFeedback(
  id: string,
  verdict: FeedbackVerdict,
  reasonCode?: string,
  reasonText?: string,
  actor = ACTOR,
): Promise<{ feedback: unknown; fpr: number | null }> {
  return request(`/api/findings/${id}/feedback`, {
    method: 'POST',
    body: { verdict, actor, reasonCode, reasonText },
  });
}

export interface FindingResponse {
  action: Record<string, unknown>;
  alert: Record<string, unknown>;
  evidence: Record<string, unknown>;
  report: {
    markdown: string;
    cited: string[];
    submitted: boolean;
    narrativeDegraded: boolean;
  };
}

export async function respondToFinding(id: string): Promise<FindingResponse> {
  return request<FindingResponse>(`/api/findings/${id}/respond`, { method: 'POST' });
}
