import { useEffect, useMemo, useState } from 'react';
import { Card, Badge } from '@/components/atoms';
import { AlertTriangle, AlertCircle } from 'lucide-react';
import { getPermits, getPermitConflicts, type PermitWire, type PermitConflict } from '@/api/permits';

interface PermitRow extends PermitWire {
  hasConflict: boolean;
  conflictDescription?: string;
}

function enrichPermits(permits: PermitWire[], conflicts: PermitConflict[]): PermitRow[] {
  const conflictByPermit = new Map<string, string>();
  for (const c of conflicts) {
    const msg = `${c.reason} (${c.permitA} ↔ ${c.permitB})`;
    conflictByPermit.set(c.permitA, msg);
    conflictByPermit.set(c.permitB, msg);
  }
  return permits.map((p) => ({
    ...p,
    hasConflict: conflictByPermit.has(p.permitId),
    conflictDescription: conflictByPermit.get(p.permitId),
  }));
}

export function PermitsPanel() {
  const [permits, setPermits] = useState<PermitRow[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [filterConflict, setFilterConflict] = useState<boolean | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('all');

  const load = async () => {
    try {
      const [active, conflictBody] = await Promise.all([getPermits(), getPermitConflicts()]);
      setPermits(enrichPermits(active, conflictBody.conflicts));
      setLoadError(null);
    } catch {
      setPermits([]);
      setLoadError('Permits unavailable — start API with `make dev`.');
    }
  };

  useEffect(() => {
    void load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  const filteredPermits = useMemo(() => {
    return permits.filter((p) => {
      if (filterConflict !== null && p.hasConflict !== filterConflict) return false;
      if (filterStatus !== 'all' && p.status !== filterStatus) return false;
      return true;
    });
  }, [permits, filterConflict, filterStatus]);

  return (
    <div className="flex flex-col gap-4 text-ink h-full select-none">
      {loadError && (
        <div className="bg-imminent/10 border border-imminent/20 text-imminent text-xs p-2 rounded flex items-center gap-2 shrink-0">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {loadError}
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3 select-none">
        <div className="flex items-center gap-1.5 bg-panel-2 p-0.5 rounded border border-line">
          <span className="text-micro font-mono text-ink-dim px-2 uppercase font-bold">CONFLICT:</span>
          {([null, true] as const).map((value) => (
            <button
              key={String(value)}
              onClick={() => setFilterConflict(value)}
              className={`h-6 px-2 text-micro font-mono font-bold rounded-sm cursor-pointer ${
                filterConflict === value
                  ? value ? 'bg-imminent/10 border-imminent/30 text-imminent' : 'bg-panel text-ink border border-line'
                  : 'text-ink-dim hover:text-ink'
              }`}
            >
              {value === null ? 'ALL' : 'CONFLICTS'}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1.5 bg-panel-2 p-0.5 rounded border border-line">
          <span className="text-micro font-mono text-ink-dim px-2 uppercase font-bold">STATUS:</span>
          {['all', 'open', 'closed'].map((status) => (
            <button
              key={status}
              onClick={() => setFilterStatus(status)}
              className={`h-6 px-2 text-micro font-mono font-bold rounded-sm cursor-pointer uppercase ${
                filterStatus === status ? 'bg-panel text-ink border border-line' : 'text-ink-dim hover:text-ink'
              }`}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto flex flex-col gap-3 scrollbar pr-1">
        {filteredPermits.map((permit) => (
          <Card
            key={permit.permitId}
            className={`flex flex-col gap-3 relative p-3 border ${
              permit.hasConflict ? 'border-imminent/30 bg-imminent/5' : 'border-line bg-panel-2/30'
            }`}
          >
            <div className="flex justify-between items-center text-xs select-none">
              <div className="flex items-center gap-2">
                <Badge variant="generic" color="ok" className="font-mono text-micro font-bold py-0.5">
                  {permit.permitId}
                </Badge>
                <span className="text-ink font-semibold">{permit.zoneId}</span>
              </div>
              <span className="text-micro font-mono text-ink-dim uppercase">[{permit.kind}]</span>
            </div>

            <div className="flex flex-col gap-1 select-text text-xs font-mono text-ink-dim">
              <span>Valid: {permit.validFrom} → {permit.validTo}</span>
              <span className="uppercase text-ink">{permit.status}</span>
            </div>

            {permit.hasConflict && permit.conflictDescription && (
              <div className="bg-imminent/5 border border-imminent/10 p-2 rounded flex items-start gap-2 text-xs text-imminent leading-normal select-text">
                <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold">SIMOPS CONFLICT:</span> {permit.conflictDescription}
                </div>
              </div>
            )}
          </Card>
        ))}

        {filteredPermits.length === 0 && !loadError && (
          <div className="flex-1 flex items-center justify-center border border-dashed border-line rounded p-6">
            <span className="text-xs text-ink-dim font-mono uppercase">NO ACTIVE PERMITS</span>
          </div>
        )}
      </div>
    </div>
  );
}
