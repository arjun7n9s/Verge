import { useEffect, useState } from 'react';
import { ShieldCheck, ShieldAlert } from 'lucide-react';
import { getAuditEntries } from '@/api';
import { auditRowsForFinding, type AuditRow } from '@/lib/auditMap';

interface FindingAuditTabProps {
  findingId: string;
}

export function FindingAuditTab({ findingId }: FindingAuditTabProps) {
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    getAuditEntries(200)
      .then((entries) => {
        if (!cancelled) setRows(auditRowsForFinding(entries, findingId));
      })
      .catch(() => {
        if (!cancelled) {
          setRows([]);
          setError('Audit ledger unavailable.');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [findingId]);

  if (loading) {
    return (
      <p className="text-xs font-mono text-ink-dim animate-pulse uppercase">Loading audit chain...</p>
    );
  }

  if (error) {
    return <p className="text-xs text-imminent font-mono">{error}</p>;
  }

  if (rows.length === 0) {
    return (
      <p className="text-xs text-ink-dim italic font-mono">
        No audit entries for this finding yet.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-2 font-mono text-xs select-text">
      {rows.map((row) => (
        <div
          key={row.entryId}
          className="p-3 border border-line bg-panel-2/30 rounded flex flex-col gap-1"
        >
          <div className="flex justify-between items-center text-ink-dim">
            <span className="font-bold text-ink uppercase flex items-center gap-1.5">
              {row.isValid ? (
                <ShieldCheck className="h-3.5 w-3.5 text-ok" />
              ) : (
                <ShieldAlert className="h-3.5 w-3.5 text-imminent" />
              )}
              {row.eventType}
            </span>
            <span className="text-micro">{row.timestamp}</span>
          </div>
          <div className="text-micro text-ink-dim">
            ACTOR: <span className="text-ink uppercase">{row.actor}</span>
          </div>
          <p className="text-ink leading-relaxed">{row.details}</p>
          <div className="text-micro text-ink-dim break-all mt-1">HASH: {row.hash}</div>
          <div className="text-micro text-ink-dim break-all">PREV: {row.prevHash}</div>
        </div>
      ))}
    </div>
  );
}
