// Verge canonical data model — TypeScript mirror of verge_schema (Python).
// Wire format is camelCase. Keep this file in lockstep with the Pydantic models;
// the contract is shared and any drift is a bug the eval harness should catch.

export type FindingState =
  | "new"
  | "acknowledged"
  | "assigned"
  | "in-progress"
  | "snoozed"
  | "escalated"
  | "suppressed-as-duplicate"
  | "resolved"
  | "closed"
  | "reopened";

export type DataQuality =
  | "live"
  | "stale"
  | "stuck-at-value"
  | "out-of-range"
  | "clock-skewed"
  | "missing";

export type LeadTimeBand = "IMMINENT" | "NEAR" | "WATCH" | "UNKNOWN";

export type EstimateQuality = "high" | "medium" | "low" | "suppressed";

export type FeedbackVerdict = "useful" | "not-useful" | "false-alarm";

export type SuppressionStatus = "pending" | "confirmed" | "rejected";

export interface Sensor {
  sensorId: string;
  kind: string;
  unit: string;
  zoneId: string;
  equipmentId?: string | null;
  expectedCadenceS: number;
  plausibleMin?: number | null;
  plausibleMax?: number | null;
  dataQuality: DataQuality;
  lastSeen?: string | null;
}

export interface Reading {
  sensorId: string;
  ts: string;
  value: number;
  dataQuality: DataQuality;
}

export interface ContributingSignal {
  kind: string;
  refId: string;
  summary: string;
  ts?: string | null;
}

export interface RiskFinding {
  findingId: string;
  createdAt: string;
  zoneId: string;
  title: string;
  state: FindingState;
  owner?: string | null;
  confidence: number;
  contributingSignals: ContributingSignal[];
  leadTimeBand: LeadTimeBand;
  leadTimeBasis?: string | null;
  estimateQuality: EstimateQuality;
  confidenceDegraded: boolean;
  confidenceDegradedBy: string[];
  counterfactual?: string | null;
  lineage: string[];
}

export interface FindingEvent {
  findingId: string;
  fromState: FindingState | null;
  toState: FindingState;
  actor: string;
  timestamp: string;
  reasonCode?: string | null;
  reasonText?: string | null;
  hash?: string | null;
  prevHash?: string | null;
}

export interface FindingFeedback {
  findingId: string;
  actor: string;
  timestamp: string;
  verdict: FeedbackVerdict;
  reasonCode?: string | null;
  reasonText?: string | null;
}

export const BAND_BOUNDS_MIN: Record<LeadTimeBand, [number | null, number | null]> = {
  IMMINENT: [0, 15],
  NEAR: [15, 45],
  WATCH: [45, null],
  UNKNOWN: [null, null],
};
