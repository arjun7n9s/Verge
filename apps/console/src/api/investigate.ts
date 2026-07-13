import { request } from './client';

/* Finding investigator agent — read-only tool loop over platform data.
   The response carries the full tool-call evidence trail (citations). */

export interface InvestigationHypothesis {
  cause: string;
  likelihood: 'high' | 'medium' | 'low' | string;
  supportedBy: string;
}

export interface InvestigationBarrier {
  action: string;
  urgency: 'immediate' | 'this-shift' | 'planned' | string;
  rationale: string;
}

export interface InvestigationBrief {
  summary: string;
  hypotheses: InvestigationHypothesis[];
  recommendedBarriers: InvestigationBarrier[];
  regulatoryRefs: { clauseId: string; relevance: string }[];
  openQuestions: string[];
}

export interface InvestigationEvidence {
  tool: string;
  arguments: Record<string, unknown>;
  result: string;
}

export interface InvestigationResult {
  findingId: string;
  brief: InvestigationBrief;
  evidence: InvestigationEvidence[];
  degraded: boolean;
  reason: string | null;
  model: string;
}

export async function investigateFinding(findingId: string): Promise<InvestigationResult> {
  return request<InvestigationResult>(
    `/api/findings/${encodeURIComponent(findingId)}/investigate`,
    { method: 'POST' },
  );
}
