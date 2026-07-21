/** Compound multi-source demo drill — start/stop/status. No frontend fiction. */

import type { WatchStatus } from '@/api/watch';

export interface DemoStatus {
  ok: boolean;
  demo: boolean;
  watch: WatchStatus & {
    mode?: string;
    scenarioId?: string | null;
    scenarioLabel?: string | null;
    coach?: string | null;
  };
}

export async function fetchDemoStatus(): Promise<DemoStatus> {
  const res = await fetch('/api/demo/status');
  if (!res.ok) throw new Error(`demo status ${res.status}`);
  return res.json() as Promise<DemoStatus>;
}

export async function startDemo(opts?: {
  scenarioId?: string;
  intervalS?: number;
  vision?: boolean;
  voice?: boolean;
  sensors?: boolean;
  fuse?: boolean;
  cognee?: boolean;
  workers?: boolean;
}): Promise<DemoStatus['watch']> {
  const res = await fetch('/api/demo/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      scenarioId: opts?.scenarioId ?? 'compound-drill',
      intervalS: opts?.intervalS,
      vision: opts?.vision,
      voice: opts?.voice,
      sensors: opts?.sensors,
      fuse: opts?.fuse,
      cognee: opts?.cognee,
      workers: opts?.workers,
    }),
  });
  if (!res.ok) throw new Error(`demo start ${res.status}`);
  const body = (await res.json()) as { watch: DemoStatus['watch'] };
  return body.watch;
}

export async function stopDemo(): Promise<DemoStatus['watch']> {
  const res = await fetch('/api/demo/stop', { method: 'POST' });
  if (!res.ok) throw new Error(`demo stop ${res.status}`);
  const body = (await res.json()) as { watch: DemoStatus['watch'] };
  return body.watch;
}
