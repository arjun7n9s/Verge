import { useEffect, useState } from 'react';
import { Card, Button } from '@/components/atoms';
import { Database, AlertCircle } from 'lucide-react';
import { getTimescaleStatus } from '@/api/platform';

export function TimescaleStatusPanel() {
  const [configured, setConfigured] = useState(false);
  const [degraded, setDegraded] = useState(false);
  const [readings, setReadings] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const refresh = () => {
    getTimescaleStatus()
      .then((s) => {
        setConfigured(s.configured);
        setDegraded(s.degraded);
        setReadings(s.readings ?? 0);
        setError(null);
      })
      .catch(() => {
        setConfigured(false);
        setDegraded(true);
        setReadings(0);
        setError('Timescale status API unavailable.');
      });
  };

  useEffect(() => {
    refresh();
  }, []);

  return (
    <Card className="p-3 border-line bg-panel-2/30 flex flex-col gap-2">
      <span className="text-micro font-mono font-bold text-ink-dim uppercase flex items-center gap-1.5">
        <Database className="h-3.5 w-3.5" />
        Timescale Telemetry (M9)
      </span>
      {error && (
        <div className="text-xs text-imminent flex items-center gap-2 font-mono">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          {error}
        </div>
      )}
      {!error && (
        <div className="text-xs font-mono text-ink-dim space-y-1">
          <div>
            Configured:{' '}
            <span className={configured ? 'text-ok' : 'text-near'}>
              {configured ? 'yes' : 'no'}
            </span>
          </div>
          {configured && (
            <>
              <div>
                Hypertable rows: <span className="text-ink">{readings}</span>
              </div>
              <div>
                Status:{' '}
                <span className={degraded ? 'text-near' : 'text-ok'}>
                  {degraded ? 'degraded' : 'healthy'}
                </span>
              </div>
            </>
          )}
          <Button variant="secondary" size="sm" onClick={refresh} className="mt-1 text-micro">
            Refresh
          </Button>
        </div>
      )}
    </Card>
  );
}
