import type { FindingState, RiskFinding } from "@verge/schema";

// Same-origin in dev (Vite proxies /api and /health to the FastAPI gateway).
const BASE = "";

export interface Ribbon {
  text: string;
  counts: Record<string, number>;
}

export interface Health {
  status: string;
  llm: { provider: string; degraded: boolean };
  audit: { entries: number; head: string; verified: boolean };
  findings: number;
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return (await r.json()) as T;
}

export const api = {
  health: () => get<Health>("/health"),
  findings: () => get<RiskFinding[]>("/api/findings"),
  ribbon: () => get<Ribbon>("/api/sensors/ribbon"),

  async transition(id: string, to: FindingState, actor: string, reasonCode?: string) {
    const r = await fetch(`${BASE}/api/findings/${id}/transition`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ to, actor, reasonCode }),
    });
    if (!r.ok) throw new Error(`transition ${id} -> ${to}: ${r.status}`);
    return (await r.json()) as RiskFinding;
  },

  async feedback(id: string, verdict: string, actor = "maya", reasonCode?: string) {
    const r = await fetch(`${BASE}/api/findings/${id}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ actor, verdict, reasonCode }),
    });
    return (await r.json()) as { fpr: number | null };
  },
};
