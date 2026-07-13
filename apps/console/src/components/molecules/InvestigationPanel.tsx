import { useState } from 'react';
import { Button } from '@/components/atoms';
import { investigateFinding, type InvestigationResult } from '@/api/investigate';
import { Bot, AlertTriangle, ChevronRight } from 'lucide-react';
import clsx from 'clsx';

/* On-demand investigation brief. Every claim is backed by a tool call shown
   in the evidence trail; a degraded run is labeled a fact sheet, never
   dressed up as analysis (P4). */

const LIKELIHOOD_COLOR: Record<string, string> = {
  high: 'text-imminent border-imminent/30 bg-imminent/10',
  medium: 'text-near border-near/30 bg-near/10',
  low: 'text-watch border-watch/30 bg-watch/10',
};

const URGENCY_COLOR: Record<string, string> = {
  immediate: 'text-imminent border-imminent/30 bg-imminent/10',
  'this-shift': 'text-near border-near/30 bg-near/10',
  planned: 'text-watch border-watch/30 bg-watch/10',
};

export function InvestigationPanel({ findingId }: { findingId: string }) {
  const [result, setResult] = useState<InvestigationResult | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showEvidence, setShowEvidence] = useState(false);

  const run = async () => {
    setRunning(true);
    setError(null);
    try {
      setResult(await investigateFinding(findingId));
    } catch {
      setError('Investigation failed — is the API running?');
    } finally {
      setRunning(false);
    }
  };

  if (!result) {
    return (
      <div className="bg-panel-2/30 border border-line p-3 rounded flex items-center justify-between gap-3">
        <div className="flex items-start gap-2">
          <Bot className="h-4 w-4 text-accent shrink-0 mt-0.5" />
          <p className="text-xs text-ink-dim leading-normal">
            Run the investigator agent: it works telemetry, permits, plant graph,
            incident memory, and OISD clauses — and cites every tool call.
          </p>
        </div>
        <Button
          variant="primary"
          size="sm"
          loading={running}
          onClick={run}
          className="text-micro font-bold uppercase shrink-0"
        >
          {running ? 'Investigating…' : 'Investigate'}
        </Button>
        {error && <span className="text-micro text-imminent font-mono">{error}</span>}
      </div>
    );
  }

  const { brief } = result;
  return (
    <div className="bg-panel-2/30 border border-line p-3 rounded flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-micro font-mono font-bold text-accent uppercase flex items-center gap-1.5">
          <Bot className="h-3.5 w-3.5" />
          {result.degraded ? 'Fact sheet (LLM unavailable)' : `Investigation brief · ${result.model}`}
        </span>
        <Button variant="ghost" size="sm" onClick={run} loading={running} className="text-micro h-6">
          Re-run
        </Button>
      </div>

      {result.degraded && (
        <div className="flex items-start gap-1.5 text-micro text-near font-mono bg-near/5 border border-near/20 rounded p-2">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          Facts only — no synthesis. {result.reason}
        </div>
      )}

      <p className="text-xs text-ink leading-relaxed">{brief.summary}</p>

      {brief.hypotheses.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <span className="text-micro font-mono font-bold text-ink-dim uppercase">Hypotheses</span>
          {brief.hypotheses.map((h, i) => (
            <div key={i} className="flex items-start gap-2 text-xs">
              <span
                className={clsx(
                  'px-1.5 py-0.5 rounded-sm border font-mono text-micro font-bold uppercase shrink-0',
                  LIKELIHOOD_COLOR[h.likelihood] ?? 'text-ink-dim border-line bg-panel',
                )}
              >
                {h.likelihood}
              </span>
              <span className="text-ink leading-normal">
                {h.cause}
                <span className="text-ink-dim font-mono text-micro"> — {h.supportedBy}</span>
              </span>
            </div>
          ))}
        </div>
      )}

      {brief.recommendedBarriers.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <span className="text-micro font-mono font-bold text-ink-dim uppercase">Recommended barriers</span>
          {brief.recommendedBarriers.map((b, i) => (
            <div key={i} className="flex items-start gap-2 text-xs">
              <span
                className={clsx(
                  'px-1.5 py-0.5 rounded-sm border font-mono text-micro font-bold uppercase shrink-0',
                  URGENCY_COLOR[b.urgency] ?? 'text-ink-dim border-line bg-panel',
                )}
              >
                {b.urgency}
              </span>
              <span className="text-ink leading-normal" title={b.rationale}>
                {b.action}
              </span>
            </div>
          ))}
        </div>
      )}

      {brief.regulatoryRefs.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {brief.regulatoryRefs.map((r, i) => (
            <span
              key={i}
              className="px-1.5 py-0.5 rounded-sm border border-line bg-panel font-mono text-micro text-ink-dim"
              title={r.relevance}
            >
              {r.clauseId}
            </span>
          ))}
        </div>
      )}

      {brief.openQuestions.length > 0 && (
        <div className="flex flex-col gap-0.5">
          <span className="text-micro font-mono font-bold text-ink-dim uppercase">Could not verify</span>
          {brief.openQuestions.map((q, i) => (
            <span key={i} className="text-micro text-ink-dim font-mono leading-normal">↳ {q}</span>
          ))}
        </div>
      )}

      <button
        onClick={() => setShowEvidence(!showEvidence)}
        className="flex items-center gap-1 text-micro font-mono text-ink-dim hover:text-ink cursor-pointer select-none"
        aria-expanded={showEvidence}
      >
        <ChevronRight className={clsx('h-3 w-3 transition-transform', showEvidence && 'rotate-90')} />
        Evidence trail — {result.evidence.length} tool call{result.evidence.length === 1 ? '' : 's'}
      </button>
      {showEvidence && (
        <div className="flex flex-col gap-1 max-h-40 overflow-y-auto scrollbar">
          {result.evidence.map((e, i) => (
            <div key={i} className="bg-panel border border-line rounded p-1.5 font-mono text-micro">
              <span className="text-accent font-bold">{e.tool}</span>
              <span className="text-ink-dim">({JSON.stringify(e.arguments)})</span>
              <p className="text-ink-dim mt-0.5 break-all leading-normal">{e.result.slice(0, 300)}{e.result.length > 300 ? '…' : ''}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
