import { useEffect, useState } from 'react';
import { Card } from '@/components/atoms';
import { Activity, AlertCircle } from 'lucide-react';
import { getOpsStatus, type OpsStatus } from '@/api/platform';

export function OpsStatusPanel() {
  const [status, setStatus] = useState<OpsStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getOpsStatus()
      .then((body) => {
        setStatus(body);
        setError(null);
      })
      .catch(() => {
        setStatus(null);
        setError('Ops status unavailable — start API with `make dev`.');
      });
  }, []);

  return (
    <Card className="p-3 border-line bg-panel-2/30 flex flex-col gap-2">
      <span className="text-micro font-mono font-bold text-ink-dim uppercase flex items-center gap-1.5">
        <Activity className="h-3.5 w-3.5" />
        Plant-IT Ops Surface (§14.6)
      </span>
      {error && (
        <div className="text-xs text-imminent flex items-center gap-2 font-mono">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          {error}
        </div>
      )}
      {status && (
        <div className="text-xs font-mono text-ink-dim space-y-1">
          <div>
            Uptime: <span className="text-ink">{Math.round(status.uptimeSeconds)}s</span>
          </div>
          <div>
            Audit:{' '}
            <span className={status.audit.verified ? 'text-ok' : 'text-imminent'}>
              {status.audit.verified ? 'verified' : 'FAILED'}
            </span>{' '}
            ({status.audit.entries} entries)
          </div>
          <div>
            Ingest: {status.ingest.sensors} sensors · {status.ingest.readings} readings
          </div>
          <div>
            LLM:{' '}
            <span className={status.llm.degraded ? 'text-near' : 'text-ok'}>
              {status.llm.degraded ? 'degraded' : 'ok'}
            </span>{' '}
            ({status.llm.provider})
          </div>
          <div>
            Vision:{' '}
            <span className={status.vision.degraded ? 'text-near' : 'text-ok'}>
              {status.vision.degraded ? 'degraded' : 'ok'}
            </span>{' '}
            ({status.vision.backend})
          </div>
          <p className="text-micro pt-1">
            Prometheus scrape: <code className="text-ink">GET /metrics</code>
          </p>
        </div>
      )}
    </Card>
  );
}
