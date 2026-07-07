import { useEffect, useState } from 'react';
import { Card } from '@/components/atoms';
import { AlertCircle, Scale } from 'lucide-react';
import { getComplianceGaps, getComplianceReport } from '@/api/platform';

export function CompliancePanel() {
  const [coverage, setCoverage] = useState<number | null>(null);
  const [gapCount, setGapCount] = useState(0);
  const [gaps, setGaps] = useState<Array<{ clauseId?: string; requirement?: string; standard?: string }>>(
    [],
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getComplianceReport(), getComplianceGaps()])
      .then(([report, gapBody]) => {
        setCoverage(Math.round((report.coverageRatio ?? 0) * 100));
        setGapCount(gapBody.gaps.length);
        setGaps(gapBody.gaps.slice(0, 5));
        setError(null);
      })
      .catch(() => {
        setCoverage(null);
        setGapCount(0);
        setGaps([]);
        setError('Compliance API unavailable.');
      });
  }, []);

  return (
    <Card className="p-3 border-line bg-panel-2/30 flex flex-col gap-2">
      <span className="text-micro font-mono font-bold text-ink-dim uppercase flex items-center gap-1.5">
        <Scale className="h-3.5 w-3.5" />
        Regulatory Compliance (OISD / Factory Act)
      </span>
      {error && (
        <div className="text-xs text-imminent flex items-center gap-2 font-mono">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          {error}
        </div>
      )}
      {coverage !== null && (
        <div className="text-xs font-mono text-ink-dim space-y-1">
          <div>
            Coverage: <span className="text-ink">{coverage}%</span> · Open gaps:{' '}
            <span className={gapCount ? 'text-near' : 'text-ok'}>{gapCount}</span>
          </div>
          {gaps.length > 0 && (
            <ul className="text-micro space-y-0.5 pt-1 list-disc list-inside">
              {gaps.map((g, i) => (
                <li key={g.clauseId ?? i}>
                  {g.standard}: {g.requirement ?? g.clauseId}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Card>
  );
}
