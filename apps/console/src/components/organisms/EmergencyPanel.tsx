import { useEffect, useMemo, useState } from 'react';
import type { RiskFinding } from '@/types';
import { Card, Button, Input } from '@/components/atoms';
import {
  getEmergencyStatus,
  declareEmergency,
  musterCheckIn,
  emergencyStandDown,
  type EmergencyStatus,
} from '@/api/emergency';
import { Siren, ShieldCheck, MapPin, UserCheck, AlertTriangle } from 'lucide-react';
import { toast } from '@/stores/toasts';
import clsx from 'clsx';

/* Emergency mode console (spec §4.4). Declaration freezes evidence, computes
   evacuation routes, and opens the muster roll-call. The operator is the
   safety interlock (P8): nothing here fires without a named approver. */

interface EmergencyPanelProps {
  activeFindings: RiskFinding[];
  onChange?: () => void;
}

export function EmergencyPanel({ activeFindings, onChange }: EmergencyPanelProps) {
  const [status, setStatus] = useState<EmergencyStatus | null>(null);
  const [approver, setApprover] = useState('');
  const [selectedFinding, setSelectedFinding] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = () => {
    getEmergencyStatus()
      .then((s) => setStatus(s))
      .catch(() => setStatus(null));
  };

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 4000);
    return () => clearInterval(interval);
  }, []);

  const candidates = useMemo(
    () =>
      [...activeFindings]
        .filter((f) => !f.shadow && f.state !== 'closed' && f.state !== 'resolved')
        .sort((a, b) => (a.leadTimeBand === 'IMMINENT' ? -1 : 1) - (b.leadTimeBand === 'IMMINENT' ? -1 : 1)),
    [activeFindings],
  );

  const act = async (fn: () => Promise<EmergencyStatus>, okMessage?: string) => {
    setBusy(true);
    setError(null);
    try {
      setStatus(await fn());
      if (okMessage) toast.ok(okMessage);
      onChange?.();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Action failed';
      setError(msg);
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  };

  if (!status?.active) {
    return (
      <Card className="p-3 border-imminent/30 bg-panel-2/30 flex flex-col gap-2.5 select-none">
        <span className="text-micro font-mono font-bold text-imminent uppercase flex items-center gap-1.5">
          <Siren className="h-3.5 w-3.5" />
          Emergency mode — standby
        </span>
        <p className="text-micro font-mono text-ink-dim leading-normal">
          Declaring freezes the finding&apos;s telemetry + worker roster into hash-bound
          evidence, computes evacuation routes, and opens the muster roll-call.
        </p>
        <div className="flex flex-col gap-1.5">
          <select
            value={selectedFinding}
            onChange={(e) => setSelectedFinding(e.target.value)}
            className="h-7 px-2 rounded border border-line text-xs bg-panel text-ink focus:outline-none"
          >
            <option value="">Select trigger finding…</option>
            {candidates.map((f) => (
              <option key={f.findingId} value={f.findingId}>
                [{f.leadTimeBand}] {f.findingId} · {f.zoneId} · {f.title.slice(0, 40)}
              </option>
            ))}
          </select>
          <div className="flex items-center gap-1.5">
            <Input
              value={approver}
              onChange={(e) => setApprover(e.target.value)}
              placeholder="Approver (required, P8)"
              className="h-7 text-xs flex-1"
              aria-label="Approver name"
            />
            <Button
              variant="danger"
              size="sm"
              disabled={!selectedFinding || !approver.trim() || busy}
              loading={busy}
              onClick={() =>
                act(
                  () => declareEmergency(selectedFinding, approver.trim()),
                  'Emergency declared — evidence frozen, muster open',
                )
              }
              className="text-micro font-bold uppercase shrink-0"
            >
              Declare
            </Button>
          </div>
        </div>
        {error && (
          <span className="text-micro font-mono text-imminent flex items-center gap-1">
            <AlertTriangle className="h-3 w-3" /> {error}
          </span>
        )}
      </Card>
    );
  }

  const muster = status.muster!;
  const evac = status.evacuation!;

  return (
    <Card className="p-3 border-imminent/60 bg-imminent/5 flex flex-col gap-2.5 select-none">
      <div className="flex items-center justify-between gap-2">
        <span className="text-micro font-mono font-bold text-imminent uppercase flex items-center gap-1.5">
          <Siren className="h-3.5 w-3.5" />
          {status.emergencyId} · ACTIVE
        </span>
        <Button
          variant="secondary"
          size="sm"
          disabled={busy || !approver.trim()}
          onClick={() => act(() => emergencyStandDown(approver.trim()), 'Emergency stood down')}
          className="text-micro font-bold uppercase h-6"
          title={approver.trim() ? 'Stand down' : 'Enter approver name below first'}
        >
          Stand down
        </Button>
      </div>

      <div className="flex flex-wrap gap-1.5 font-mono text-micro">
        <span className="px-1.5 py-0.5 rounded-sm border border-imminent/40 bg-imminent/10 text-imminent">
          zones: {status.affectedZones?.join(', ')}
        </span>
        <span className="px-1.5 py-0.5 rounded-sm border border-line bg-panel text-ink-dim" title={status.evidenceFreeze?.hash}>
          <ShieldCheck className="h-3 w-3 inline mr-0.5" />
          evidence frozen · {status.evidenceFreeze?.hash.slice(0, 10)}…
        </span>
        <span className="px-1.5 py-0.5 rounded-sm border border-line bg-panel text-ink-dim">
          declared by {status.declaredBy}
        </span>
      </div>

      {/* Evacuation routes */}
      <div className="flex flex-col gap-1">
        <span className="text-micro font-mono font-bold text-ink-dim uppercase flex items-center gap-1">
          <MapPin className="h-3 w-3" /> Evacuation routes
        </span>
        <div className="flex flex-col gap-0.5 font-mono text-micro max-h-24 overflow-y-auto scrollbar">
          {Object.values(evac.routes).map((r) => (
            <span key={r.zoneId} className={clsx(r.trapped ? 'text-imminent font-bold' : 'text-ink-dim')}>
              {r.trapped
                ? `${r.zoneId} — NO SAFE ROUTE (rescue priority)`
                : `${r.route.join(' → ')} ⇒ ${r.musterId}`}
            </span>
          ))}
        </div>
      </div>

      {/* Muster roll-call */}
      <div className="flex flex-col gap-1">
        <div className="flex items-center justify-between">
          <span className="text-micro font-mono font-bold text-ink-dim uppercase flex items-center gap-1">
            <UserCheck className="h-3 w-3" /> Muster roll-call
          </span>
          <span
            className={clsx(
              'text-micro font-mono font-bold tabular-nums',
              muster.allAccounted ? 'text-ok' : 'text-near',
            )}
          >
            {muster.accounted.length}/{muster.expected} accounted
          </span>
        </div>
        {muster.missing.length > 0 && (
          <div className="flex flex-col gap-0.5 max-h-28 overflow-y-auto scrollbar">
            {muster.missing.map((m) => (
              <div
                key={m.workerId}
                className="flex items-center justify-between gap-2 font-mono text-micro bg-panel border border-line rounded px-1.5 py-1"
              >
                <span className="text-ink truncate">
                  {m.name || m.workerId}
                  <span className="text-ink-dim"> · last seen {m.lastKnownZone}{m.lastFixStale ? ' (stale)' : ''}</span>
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={busy || !evac.usableMusterPoints.length}
                  onClick={() =>
                    act(() =>
                      musterCheckIn(
                        m.workerId,
                        evac.usableMusterPoints[0]?.musterId ?? 'MP-UNKNOWN',
                        approver.trim() || 'muster-officer',
                      ),
                    )
                  }
                  className="text-micro h-5 px-1.5 shrink-0 text-ok hover:bg-ok/10"
                >
                  Check in
                </Button>
              </div>
            ))}
          </div>
        )}
        {muster.allAccounted && (
          <span className="text-micro font-mono text-ok font-bold">ALL PERSONNEL ACCOUNTED FOR</span>
        )}
      </div>

      <Input
        value={approver}
        onChange={(e) => setApprover(e.target.value)}
        placeholder="Acting officer (for check-ins / stand-down)"
        className="h-6 text-micro"
        aria-label="Acting officer"
      />
      {error && (
        <span className="text-micro font-mono text-imminent flex items-center gap-1">
          <AlertTriangle className="h-3 w-3" /> {error}
        </span>
      )}
    </Card>
  );
}
