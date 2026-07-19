/**
 * Vision Ops strip — last detections + camera id (Phase 2B).
 * Mounted on the board; empty when no detections (honest, not fake).
 */
import { useEffect, useState } from 'react';
import { Camera } from 'lucide-react';
import clsx from 'clsx';

interface VisionRow {
  detectionId: string;
  ts: string;
  cameraId: string;
  zoneId: string;
  label: string;
  confidence: number;
  frameUri?: string | null;
}

export function VisionOpsStrip({ className }: { className?: string }) {
  const [rows, setRows] = useState<VisionRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const res = await fetch('/api/vision/events?limit=6');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const body = (await res.json()) as { detections?: VisionRow[] };
        if (!cancelled) {
          setRows(body.detections ?? []);
          setError(null);
        }
      } catch {
        if (!cancelled) setError('vision feed offline');
      }
    };
    void load();
    const id = setInterval(() => void load(), 5000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <div
      className={clsx(
        'border-b border-line bg-panel px-4 py-1.5 flex items-center gap-3 min-h-[28px] overflow-hidden',
        className,
      )}
      aria-label="Vision ops detections"
    >
      <span className="flex items-center gap-1.5 shrink-0 text-micro font-mono uppercase tracking-[0.08em] text-ink-dim">
        <Camera className="h-3 w-3" />
        Vision
      </span>
      {error ? (
        <span className="text-xs text-ink-dim truncate">{error}</span>
      ) : rows.length === 0 ? (
        <span className="text-xs text-ink-dim truncate">No recent detections</span>
      ) : (
        <div className="flex gap-4 min-w-0 overflow-x-auto">
          {rows.slice(0, 5).map((d) => (
            <span key={d.detectionId} className="text-xs text-ink whitespace-nowrap shrink-0">
              <span className="font-mono text-ink-dim mr-1">{d.cameraId}</span>
              {d.label}
              <span className="font-mono text-ink-dim ml-1">
                {d.zoneId} · {(d.confidence * 100).toFixed(0)}%
              </span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
