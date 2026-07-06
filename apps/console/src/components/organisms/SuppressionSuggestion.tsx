import { useState } from 'react';
import type { RiskFinding } from '@/types';
import { Card, Button } from '@/components/atoms';
import { Merge, Check, X } from 'lucide-react';
import { transitionFinding } from '@/api';

interface SuppressionSuggestionProps {
  activeFindings: RiskFinding[];
  onChange: () => void;
}

function duplicateGroups(findings: RiskFinding[]): Array<{ primary: RiskFinding; duplicate: RiskFinding }> {
  const open = findings.filter((f) => f.state === 'new' && !f.shadow);
  const byKey = new Map<string, RiskFinding[]>();
  for (const f of open) {
    const key = `${f.zoneId}::${f.title}`;
    byKey.set(key, [...(byKey.get(key) ?? []), f]);
  }
  const pairs: Array<{ primary: RiskFinding; duplicate: RiskFinding }> = [];
  for (const group of byKey.values()) {
    if (group.length < 2) continue;
    const sorted = [...group].sort((a, b) => a.findingId.localeCompare(b.findingId));
    const [primary, ...rest] = sorted;
    for (const duplicate of rest) {
      pairs.push({ primary, duplicate });
    }
  }
  return pairs;
}

export function SuppressionSuggestion({ activeFindings, onChange }: SuppressionSuggestionProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const suggestions = duplicateGroups(activeFindings);

  if (suggestions.length === 0) return null;

  const handleConfirm = async (duplicate: RiskFinding, primary: RiskFinding) => {
    setIsSubmitting(true);
    try {
      await transitionFinding(
        duplicate.findingId,
        'suppressed-as-duplicate',
        `Merged into ${primary.findingId}`,
        'duplicate-confirmed',
      );
      onChange();
    } catch (err) {
      console.error('[SuppressionSuggestion] Merge failed:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async (duplicateId: string) => {
    setIsSubmitting(true);
    try {
      await transitionFinding(
        duplicateId,
        'acknowledged',
        'Operator rejected duplicate suppression suggestion.',
        'duplicate-rejected',
      );
      onChange();
    } catch (err) {
      console.error('[SuppressionSuggestion] Rejection failed:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col gap-2 shrink-0 select-none">
      {suggestions.map(({ primary, duplicate }) => (
        <Card
          key={duplicate.findingId}
          className="border-accent/30 bg-accent/5 p-3 flex flex-col md:flex-row md:items-center justify-between gap-3 text-ink"
        >
          <div className="flex items-start gap-2.5">
            <div className="p-1.5 bg-accent/15 border border-accent/25 rounded text-accent shrink-0 mt-0.5">
              <Merge className="h-4 w-4" />
            </div>
            <div className="flex flex-col gap-0.5">
              <div className="text-xs font-bold flex items-center gap-1.5">
                <span>COLLAPSE SUGGESTION: duplicate risk finding detected</span>
              </div>
              <p className="text-xs text-ink-dim leading-relaxed">
                Merge <code className="text-accent">{duplicate.findingId}</code> into{' '}
                <code className="text-accent">{primary.findingId}</code> ({primary.title}) in{' '}
                {duplicate.zoneId}.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0 self-end md:self-center">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleReject(duplicate.findingId)}
              disabled={isSubmitting}
              className="text-ink-dim hover:text-imminent hover:bg-imminent/10 hover:border-imminent/20"
              icon={<X className="h-3.5 w-3.5" />}
            >
              Reject
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => handleConfirm(duplicate, primary)}
              disabled={isSubmitting}
              className="bg-accent/20 border-accent/40 text-accent hover:bg-accent/30"
              icon={<Check className="h-3.5 w-3.5" />}
            >
              Approve Merge
            </Button>
          </div>
        </Card>
      ))}
    </div>
  );
}
