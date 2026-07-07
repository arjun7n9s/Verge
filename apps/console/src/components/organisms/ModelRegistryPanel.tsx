import { useEffect, useState } from 'react';
import { Card } from '@/components/atoms';
import { AlertCircle, Cpu } from 'lucide-react';
import { getModelRegistry, type ModelCard } from '@/api/platform';

export function ModelRegistryPanel() {
  const [models, setModels] = useState<ModelCard[]>([]);
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getModelRegistry()
      .then((body) => {
        setModels(body.models.slice(0, 6));
        setSummary(body.summary);
        setError(null);
      })
      .catch(() => {
        setModels([]);
        setSummary(null);
        setError('Model registry unavailable.');
      });
  }, []);

  return (
    <Card className="p-3 border-line bg-panel-2/30 flex flex-col gap-2">
      <span className="text-micro font-mono font-bold text-ink-dim uppercase flex items-center gap-1.5">
        <Cpu className="h-3.5 w-3.5" />
        Model Registry (MLOps)
      </span>
      {error && (
        <div className="text-xs text-imminent flex items-center gap-2 font-mono">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          {error}
        </div>
      )}
      {summary && (
        <div className="text-xs font-mono text-ink-dim space-y-1">
          <div>
            Models tracked: <span className="text-ink">{String(summary.total ?? models.length)}</span>
          </div>
          {models.map((m) => (
            <div key={`${m.name}-${m.version}`} className="text-micro">
              {m.name} v{m.version}{' '}
              <span className="text-accent uppercase">{m.stage}</span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
