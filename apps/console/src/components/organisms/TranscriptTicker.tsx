/**
 * Live radio transcript ticker — Mission Control strip (Phase 2C).
 * Role-gated: Safety_Engineer / administrator. Polls /api/voice/events.
 */
import { useEffect, useState } from 'react';
import { Radio } from 'lucide-react';
import { useAuthStore } from '@/stores/auth';
import clsx from 'clsx';

interface VoiceEventRow {
  eventId: string;
  ts: string;
  transcript: string;
  zoneId?: string | null;
  hazards?: string[];
  source?: string;
}

const ALLOWED = new Set(['Safety_Engineer', 'administrator']);

export function TranscriptTicker({ className }: { className?: string }) {
  const user = useAuthStore((s) => s.user);
  const roles = user?.roles ?? [];
  // Dev without auth: show ticker. With auth: Safety_Engineer / administrator only.
  const allowed = !user || roles.some((r) => ALLOWED.has(r));
  const [events, setEvents] = useState<VoiceEventRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!allowed) return;
    let cancelled = false;
    const load = async () => {
      try {
        const res = await fetch('/api/voice/events?limit=8');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const body = (await res.json()) as { events?: VoiceEventRow[] };
        if (!cancelled) {
          setEvents(body.events ?? []);
          setError(null);
        }
      } catch {
        if (!cancelled) setError('voice feed offline');
      }
    };
    void load();
    const id = setInterval(() => void load(), 5000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [allowed]);

  if (!allowed) return null;

  return (
    <div
      className={clsx(
        'border-b border-line bg-panel px-4 py-1.5 flex items-center gap-3 min-h-[28px] overflow-hidden',
        className,
      )}
      aria-label="Live radio transcripts"
    >
      <span className="flex items-center gap-1.5 shrink-0 text-micro font-mono uppercase tracking-[0.08em] text-ink-dim">
        <Radio className="h-3 w-3" />
        Radio
      </span>
      {error ? (
        <span className="text-xs text-ink-dim truncate">{error}</span>
      ) : events.length === 0 ? (
        <span className="text-xs text-ink-dim truncate">No recent radio events</span>
      ) : (
        <div className="flex-1 min-w-0 overflow-hidden">
          <div className="flex gap-6 animate-none">
            {events.slice(0, 4).map((ev) => (
              <span key={ev.eventId} className="text-xs text-ink whitespace-nowrap shrink-0">
                <span className="font-mono text-ink-dim mr-1.5">
                  {ev.zoneId || '—'}
                </span>
                {(ev.transcript || '').slice(0, 96)}
                {(ev.transcript || '').length > 96 ? '…' : ''}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
