import { useEffect, useState } from 'react';
import { Card, Badge } from '@/components/atoms';
import { ClipboardCheck, AlertCircle } from 'lucide-react';
import { getCommissionSummary } from '@/api/platform';

const STATUS_COLOR: Record<string, 'ok' | 'near' | 'imminent' | 'unknown'> = {
  pass: 'ok',
  warn: 'near',
  fail: 'imminent',
};

export function CommissioningPanel() {
  const [ready, setReady] = useState<boolean | null>(null);
  const [checks, setChecks] = useState<
    Array<{ step: string; status: string; detail: string }>
  >([]);
  const [dryRunCount, setDryRunCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCommissionSummary()
      .then((body) => {
        setReady(body.ready);
        setChecks(body.checks);
        setDryRunCount(body.dryRun?.length ?? 0);
        setError(null);
      })
      .catch(() => {
        setReady(null);
        setChecks([]);
        setDryRunCount(0);
        setError('Commissioning API unavailable.');
      });
  }, []);

  return (
    <Card className="p-3 border-line bg-panel-2/30 flex flex-col gap-2 md:col-span-2">
      <span className="text-micro font-mono font-bold text-ink-dim uppercase flex items-center gap-1.5">
        <ClipboardCheck className="h-3.5 w-3.5" />
        Plant Commissioning (§14.5)
      </span>
      {error && (
        <div className="text-xs text-imminent flex items-center gap-2 font-mono">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          {error}
        </div>
      )}
      {ready !== null && (
        <>
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="text-ink-dim">Readiness:</span>
            <Badge variant="generic" color={ready ? 'ok' : 'near'}>
              {ready ? 'SHADOW READY' : 'NOT READY'}
            </Badge>
            <span className="text-ink-dim">· Dry-runs: {dryRunCount}</span>
          </div>
          <ul className="text-micro font-mono space-y-1 pt-1">
            {checks.map((c) => (
              <li key={c.step} className="flex items-start gap-2">
                <Badge variant="generic" color={STATUS_COLOR[c.status] ?? 'unknown'} className="shrink-0">
                  {c.status}
                </Badge>
                <span>
                  <span className="text-ink">{c.step}</span>
                  <span className="text-ink-dim"> — {c.detail}</span>
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </Card>
  );
}
