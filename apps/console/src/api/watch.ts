/** Continuous WatchLoop — start/stop/status. No frontend fiction. */

export interface WatchStatus {
  running: boolean;
  mode?: string;
  scenarioId?: string | null;
  scenarioLabel?: string | null;
  coach?: string | null;
  startedAt?: string | null;
  intervalS: number;
  ticks: number;
  lastTickAt?: string | null;
  lastError?: string | null;
  legs: Record<string, boolean>;
  counts: Record<string, number>;
  last?: Record<string, unknown>;
}

export async function fetchWatchStatus(): Promise<WatchStatus> {
  const res = await fetch('/api/watch/status');
  if (!res.ok) throw new Error(`watch status ${res.status}`);
  return res.json() as Promise<WatchStatus>;
}

export async function startWatch(opts?: {
  intervalS?: number;
  vision?: boolean;
  voice?: boolean;
  sensors?: boolean;
  fuse?: boolean;
  cognee?: boolean;
}): Promise<WatchStatus> {
  const res = await fetch('/api/watch/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(opts ?? {}),
  });
  if (!res.ok) throw new Error(`watch start ${res.status}`);
  const body = (await res.json()) as { watch: WatchStatus };
  return body.watch;
}

export async function stopWatch(): Promise<WatchStatus> {
  const res = await fetch('/api/watch/stop', { method: 'POST' });
  if (!res.ok) throw new Error(`watch stop ${res.status}`);
  const body = (await res.json()) as { watch: WatchStatus };
  return body.watch;
}
