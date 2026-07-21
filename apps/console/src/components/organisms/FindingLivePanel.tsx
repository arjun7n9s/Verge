/**
 * Finding Live block — live cam, radio+audio, synced incident timeline (§6.2).
 */
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Camera, Radio, Network, Clock } from 'lucide-react';
import type { RiskFinding } from '@/types';
import { getFindingTelemetry, type FindingTelemetry } from '@/api/telemetry';
import { getPermits, type PermitWire } from '@/api/permits';
import {
  displayableAudioSrc,
  displayableFrameSrc,
  fetchCameras,
  fetchVisionEvents,
  fetchVoiceEvents,
  type CameraRow,
  type VisionDetectionRow,
  type VoiceEventRow,
} from '@/api/liveOps';
import clsx from 'clsx';

type TimelineKind = 'vision' | 'radio' | 'sensor';

interface TimelineMark {
  id: string;
  kind: TimelineKind;
  ts: number;
  label: string;
  detail?: string;
  frameUri?: string | null;
  audioClipUri?: string | null;
}

const LEG_LABEL: Record<TimelineKind, string> = {
  vision: 'Camera',
  radio: 'Radio',
  sensor: 'Sensor',
};

function parseTs(ts: string | undefined): number {
  if (!ts) return 0;
  const n = Date.parse(ts);
  return Number.isFinite(n) ? n : 0;
}

function hasThreeLegLineage(lineage: string[] | undefined): boolean {
  const kinds = new Set((lineage || []).map((x) => String(x).split(':')[0]));
  return kinds.has('voice') && kinds.has('reading') && kinds.has('vision');
}

export function FindingLivePanel({ finding }: { finding: RiskFinding }) {
  const [telemetry, setTelemetry] = useState<FindingTelemetry | null>(null);
  const [telemetryErr, setTelemetryErr] = useState<string | null>(null);
  const [permits, setPermits] = useState<PermitWire[]>([]);
  const [visionHits, setVisionHits] = useState<VisionDetectionRow[]>([]);
  const [radio, setRadio] = useState<VoiceEventRow[]>([]);
  const [cameras, setCameras] = useState<CameraRow[]>([]);
  const [cursor, setCursor] = useState(0);

  useEffect(() => {
    let cancelled = false;
    getFindingTelemetry(finding.findingId)
      .then((t) => {
        if (!cancelled) {
          setTelemetry(t);
          setTelemetryErr(null);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setTelemetry(null);
          setTelemetryErr('Telemetry unavailable');
        }
      });

    getPermits()
      .then((all) => {
        if (cancelled) return;
        setPermits(all.filter((p) => p.zoneId === finding.zoneId));
      })
      .catch(() => {
        if (!cancelled) setPermits([]);
      });

    Promise.allSettled([
      fetchVisionEvents(30),
      fetchVoiceEvents(20),
      fetchCameras(),
    ]).then(([vRes, rRes, cRes]) => {
      if (cancelled) return;
      if (vRes.status === 'fulfilled') {
        setVisionHits(vRes.value.filter((d) => d.zoneId === finding.zoneId));
      }
      if (rRes.status === 'fulfilled') {
        setRadio(
          rRes.value.filter((e) => !e.zoneId || e.zoneId === finding.zoneId).slice(0, 8),
        );
      }
      if (cRes.status === 'fulfilled') {
        setCameras(cRes.value);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [finding.findingId, finding.zoneId]);

  const zoneCam =
    cameras.find((c) => c.zoneId === finding.zoneId && c.hasSource) ??
    cameras.find((c) => c.zoneId === finding.zoneId) ??
    null;

  const marks = useMemo(() => {
    const out: TimelineMark[] = [];
    for (const v of visionHits) {
      out.push({
        id: `v-${v.detectionId}`,
        kind: 'vision',
        ts: parseTs(v.ts),
        label: v.label,
        detail: `${v.cameraId} · ${(v.confidence * 100).toFixed(0)}%`,
        frameUri: v.frameUri,
      });
    }
    for (const e of radio) {
      out.push({
        id: `r-${e.eventId}`,
        kind: 'radio',
        ts: parseTs(e.ts),
        label: e.transcript.slice(0, 72) || e.eventId,
        detail: e.zoneId || finding.zoneId,
        audioClipUri: e.audioClipUri,
      });
    }
    for (const s of telemetry?.series ?? []) {
      const last = s.points[s.points.length - 1];
      if (!last) continue;
      out.push({
        id: `s-${s.sensorId}`,
        kind: 'sensor',
        ts: parseTs(last.ts),
        label: s.sensorId,
        detail:
          typeof last.value === 'number'
            ? `${last.value.toFixed(2)}${s.unit ? ` ${s.unit}` : ''}`
            : String(last.value),
      });
    }
    out.sort((a, b) => a.ts - b.ts);
    return out;
  }, [visionHits, radio, telemetry, finding.zoneId]);

  useEffect(() => {
    if (marks.length) setCursor(marks.length - 1);
  }, [marks.length]);

  const active = marks[cursor] ?? null;
  const activeFrame =
    displayableFrameSrc(active?.frameUri) ??
    displayableFrameSrc(visionHits.find((v) => displayableFrameSrc(v.frameUri))?.frameUri);
  const activeAudio = displayableAudioSrc(active?.audioClipUri);
  const liveSrc = zoneCam?.streamPath || zoneCam?.snapshotPath || null;

  const tMin = marks[0]?.ts ?? 0;
  const tMax = marks[marks.length - 1]?.ts ?? 1;
  const span = Math.max(1, tMax - tMin);

  const activePermits = permits.filter((p) => {
    const s = (p.status || '').toLowerCase();
    return s === 'active' || s === 'open' || s === 'issued' || !s;
  });

  const threeLeg = hasThreeLegLineage(finding.lineage);

  return (
    <div className="flex flex-col gap-4">
      {threeLeg && (
        <div className="border border-line rounded-md bg-bg/50 px-3 py-2.5">
          <p className="text-sm text-ink leading-snug">
            Converged from radio · LEL · camera — single streams were weak alone.
          </p>
          <p className="text-xs text-ink-dim mt-1 leading-relaxed">
            Advisory next: hold hot work, clear the bay, confirm LEL — then Investigate.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {/* Live zone camera */}
        <div className="border border-line rounded-md bg-panel overflow-hidden flex flex-col min-h-[160px]">
          <div className="px-2.5 py-1.5 border-b border-line text-micro font-mono uppercase tracking-[0.08em] text-ink-dim flex items-center gap-1.5">
            <Camera className="h-3 w-3" />
            Zone camera
            {zoneCam && (
              <span className="normal-case tracking-normal ml-1 truncate">
                {zoneCam.cameraId}
                {zoneCam.sourceKind === 'demo' ? ' · DEMO' : zoneCam.hasSource ? ' · LIVE' : ''}
              </span>
            )}
          </div>
          <div className="flex-1 flex items-center justify-center p-2 bg-bg/40 min-h-[120px] relative">
            {liveSrc ? (
              <img
                src={liveSrc}
                alt={`${zoneCam?.cameraId ?? 'zone'} live`}
                className="max-h-40 max-w-full object-contain border border-line"
              />
            ) : activeFrame ? (
              <img
                src={activeFrame}
                alt="Timeline frame"
                className="max-h-40 max-w-full object-contain border border-line"
              />
            ) : visionHits[0] ? (
              <span className="text-xs text-ink-dim text-center px-3 font-mono">
                {visionHits[0].cameraId} · {visionHits[0].label}
                <span className="block mt-1 text-micro">No live source / displayable frame</span>
              </span>
            ) : (
              <span className="text-xs text-ink-dim text-center px-3">
                No camera source for {finding.zoneId}
              </span>
            )}
          </div>
        </div>

        {/* Radio */}
        <div className="border border-line rounded-md bg-panel overflow-hidden flex flex-col min-h-[160px]">
          <div className="px-2.5 py-1.5 border-b border-line text-micro font-mono uppercase tracking-[0.08em] text-ink-dim flex items-center gap-1.5">
            <Radio className="h-3 w-3" />
            Zone radio
          </div>
          <div className="flex-1 overflow-y-auto scrollbar px-2.5 py-2">
            {radio.length === 0 ? (
              <span className="text-xs text-ink-dim">No recent radio for this zone</span>
            ) : (
              <ul className="flex flex-col gap-2">
                {radio.map((ev) => {
                  const audioSrc = displayableAudioSrc(ev.audioClipUri);
                  return (
                    <li key={ev.eventId} className="text-xs text-ink leading-snug">
                      <span className="font-mono text-ink-dim mr-1">{ev.zoneId || '—'}</span>
                      {ev.transcript}
                      {audioSrc && (
                        <audio controls preload="none" src={audioSrc} className="mt-1 w-full h-7" />
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      </div>

      {/* Synced incident timeline */}
      <div className="border border-line rounded-md bg-panel p-3 flex flex-col gap-3">
        <div className="flex items-center gap-1.5 text-micro font-mono uppercase tracking-[0.08em] text-ink-dim">
          <Clock className="h-3 w-3" />
          Incident timeline
          <span className="normal-case tracking-normal ml-auto tabular-nums">
            {marks.length} marks · Camera / Radio / Sensor
          </span>
        </div>

        {marks.length === 0 ? (
          <span className="text-xs text-ink-dim">
            No zone events yet — timeline fills as vision, radio, and sensors arrive
          </span>
        ) : (
          <>
            <div className="flex gap-3 text-micro font-mono uppercase tracking-[0.08em] text-ink-dim">
              <span>
                <span className="inline-block w-2 h-2 rounded-sm border border-watch bg-watch/40 mr-1 align-middle" />
                Camera
              </span>
              <span>
                <span className="inline-block w-2 h-2 rounded-sm border border-ink/50 bg-panel-2 mr-1 align-middle" />
                Radio
              </span>
              <span>
                <span className="inline-block w-2 h-2 rounded-sm border border-line bg-bg mr-1 align-middle" />
                Sensor
              </span>
            </div>
            <div className="relative h-10">
              <div className="absolute inset-x-0 top-1/2 h-px bg-line" />
              {marks.map((m, i) => {
                const pct = ((m.ts - tMin) / span) * 100;
                return (
                  <button
                    key={m.id}
                    type="button"
                    title={`${LEG_LABEL[m.kind]}: ${m.label}`}
                    onClick={() => setCursor(i)}
                    className={clsx(
                      'absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-2.5 h-2.5 rounded-sm border',
                      i === cursor
                        ? 'border-ink bg-ink scale-125'
                        : m.kind === 'vision'
                          ? 'border-watch bg-watch/40'
                          : m.kind === 'radio'
                            ? 'border-ink/50 bg-panel-2'
                            : 'border-line bg-bg',
                    )}
                    style={{ left: `${pct}%` }}
                  />
                );
              })}
            </div>
            <input
              type="range"
              min={0}
              max={Math.max(0, marks.length - 1)}
              value={cursor}
              onChange={(e) => setCursor(Number(e.target.value))}
              className="w-full accent-ink"
              aria-label="Scrub incident timeline"
            />
            {active && (
              <div className="flex flex-col sm:flex-row gap-3 items-start">
                <div className="flex-1 min-w-0">
                  <div className="text-micro font-mono uppercase text-ink-dim">
                    {LEG_LABEL[active.kind]}
                  </div>
                  <div className="text-sm text-ink mt-0.5">{active.label}</div>
                  {active.detail && (
                    <div className="text-micro font-mono text-ink-dim mt-0.5">{active.detail}</div>
                  )}
                  {active.ts > 0 && (
                    <div className="text-micro font-mono text-ink-dim mt-1 tabular-nums">
                      {new Date(active.ts).toISOString().replace('T', ' ').slice(0, 19)}Z
                    </div>
                  )}
                </div>
                {activeFrame && active.kind === 'vision' && (
                  <img
                    src={activeFrame}
                    alt="Selected vision still"
                    className="max-h-24 border border-line object-contain"
                  />
                )}
                {activeAudio && active.kind === 'radio' && (
                  <audio controls autoPlay src={activeAudio} className="w-full sm:w-56 h-8" />
                )}
              </div>
            )}
          </>
        )}
      </div>

      {/* Telemetry summary */}
      <div className="border border-line rounded-md bg-panel p-3 flex flex-col gap-2">
        <span className="text-micro font-mono uppercase tracking-[0.08em] text-ink-dim">
          Telemetry window
        </span>
        {telemetryErr ? (
          <span className="text-xs text-ink-dim font-mono">{telemetryErr}</span>
        ) : !telemetry?.series?.length ? (
          <span className="text-xs text-ink-dim">No sensor series for this finding</span>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {telemetry.series.slice(0, 6).map((s) => {
              const last = s.points[s.points.length - 1];
              return (
                <li
                  key={s.sensorId}
                  className="px-2 py-1 border border-line rounded-sm bg-bg font-mono text-micro text-ink"
                >
                  {s.sensorId}
                  {last != null && (
                    <span className="text-ink-dim ml-1.5 tabular-nums">
                      {typeof last.value === 'number' ? last.value.toFixed(2) : last.value}
                      {s.unit ? ` ${s.unit}` : ''}
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* Permits */}
      <div className="border border-line rounded-md bg-panel p-3 flex flex-col gap-2">
        <span className="text-micro font-mono uppercase tracking-[0.08em] text-ink-dim">
          Active permits · {finding.zoneId}
        </span>
        {activePermits.length === 0 ? (
          <span className="text-xs text-ink-dim">No active permits in this zone</span>
        ) : (
          <ul className="flex flex-col gap-1">
            {activePermits.slice(0, 6).map((p) => (
              <li key={p.permitId} className="text-xs font-mono text-ink flex gap-2">
                <span className="text-ink-dim">{p.permitId}</span>
                <span>{p.kind}</span>
                <span className="text-ink-dim">{p.status}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <Link
        to="/graph"
        className="inline-flex items-center gap-1.5 text-micro font-mono uppercase tracking-[0.08em] text-ink-dim hover:text-ink transition-colors w-fit"
      >
        <Network className="h-3 w-3" />
        Open plant graph
      </Link>
    </div>
  );
}
