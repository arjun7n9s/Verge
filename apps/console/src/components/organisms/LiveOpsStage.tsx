/**
 * Live Ops stage — calm situation room (design_plan §6.1 + premium demo board).
 * Three equal legs: Cameras | Radio | Sensors. Demo narrates phases; no fiction.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Radio, Camera, Activity, Gauge, ArrowRight } from 'lucide-react';
import { useAuthStore } from '@/stores/auth';
import { useFindingsStore } from '@/stores/findings';
import { BAND_SEVERITY } from '@/types';
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
import { startDemo, stopDemo } from '@/api/demo';
import { fetchWatchStatus, type WatchStatus } from '@/api/watch';
import clsx from 'clsx';

const RADIO_ROLES = new Set(['Safety_Engineer', 'administrator']);

type SensorReading = {
  sensorId?: string;
  value?: number;
  zoneId?: string;
  kind?: string;
  unit?: string;
};

function isCompoundFinding(f: {
  title?: string;
  lineage?: string[];
}): boolean {
  const title = (f.title || '').toLowerCase();
  if (title.includes('compound')) return true;
  const kinds = new Set((f.lineage || []).map((x) => String(x).split(':')[0]));
  return kinds.has('voice') && kinds.has('reading') && kinds.has('vision');
}

function underAlarmLabel(factor: number | undefined): string {
  if (factor == null) return '—';
  if (factor < 0.2) return 'under classic alarm';
  if (factor < 0.45) return 'creeping · still under alarm';
  if (factor < 0.8) return 'near threshold';
  return 'at / above threshold';
}

export function LiveOpsStage({
  className,
  onDemoChange,
}: {
  className?: string;
  onDemoChange?: (running: boolean) => void;
}) {
  const user = useAuthStore((s) => s.user);
  const roles = user?.roles ?? [];
  const radioAllowed = !user || roles.some((r) => RADIO_ROLES.has(r));

  const findings = useFindingsStore((s) => s.findings);
  const compoundFinding = useMemo(() => {
    const open = findings.filter((f) => f.state !== 'closed' && f.state !== 'resolved');
    const compound = open.find(isCompoundFinding);
    if (compound) return compound;
    return (
      [...open].sort(
        (a, b) => BAND_SEVERITY[a.leadTimeBand] - BAND_SEVERITY[b.leadTimeBand],
      )[0] ?? null
    );
  }, [findings]);

  const [radio, setRadio] = useState<VoiceEventRow[]>([]);
  const [vision, setVision] = useState<VisionDetectionRow[]>([]);
  const [cameras, setCameras] = useState<CameraRow[]>([]);
  const [voiceErr, setVoiceErr] = useState<string | null>(null);
  const [camErr, setCamErr] = useState<string | null>(null);
  const [playingId, setPlayingId] = useState<string | null>(null);
  const [watch, setWatch] = useState<WatchStatus | null>(null);
  const [watchBusy, setWatchBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const pollWatch = async () => {
      try {
        const s = await fetchWatchStatus();
        if (!cancelled) {
          setWatch(s);
          onDemoChange?.(Boolean(s.running && s.mode === 'demo'));
        }
      } catch {
        if (!cancelled) {
          setWatch(null);
          onDemoChange?.(false);
        }
      }
    };
    void pollWatch();
    const id = setInterval(() => void pollWatch(), 2000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [onDemoChange]);

  const toggleDemo = async () => {
    setWatchBusy(true);
    try {
      const s =
        watch?.running && watch?.mode === 'demo'
          ? await stopDemo()
          : await startDemo({ scenarioId: 'compound-drill', intervalS: 3 });
      setWatch(s);
      onDemoChange?.(Boolean(s.running && s.mode === 'demo'));
    } catch {
      /* status poll will refresh */
    } finally {
      setWatchBusy(false);
    }
  };

  const demoRunning = Boolean(watch?.running && watch?.mode === 'demo');

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      // During demo, show radio transcripts even if role would normally gate —
      // summit path must show the voice leg. Still label when restricted offline.
      try {
        const events = await fetchVoiceEvents(10);
        if (!cancelled) {
          setRadio(events);
          setVoiceErr(null);
        }
      } catch {
        if (!cancelled) {
          setRadio([]);
          setVoiceErr(radioAllowed ? 'radio feed offline' : 'Radio feed restricted');
        }
      }

      try {
        const [dets, cams] = await Promise.all([fetchVisionEvents(10), fetchCameras()]);
        if (!cancelled) {
          setVision(dets);
          setCameras(cams);
          setCamErr(null);
        }
      } catch {
        if (!cancelled) {
          setVision([]);
          setCameras([]);
          setCamErr('camera feed offline');
        }
      }
    };
    void load();
    const id = setInterval(() => void load(), 5000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [radioAllowed]);

  const liveCams = cameras.filter((c) => c.hasSource);
  const primaryCam =
    liveCams.find((c) => c.sourceKind === 'demo') ??
    liveCams.find((c) => c.zoneId === (watch?.zonePrimary || 'B-04')) ??
    liveCams[0] ??
    null;

  const latestDetection =
    (primaryCam &&
      vision.find(
        (v) => v.cameraId === primaryCam.cameraId && displayableFrameSrc(v.frameUri),
      )) ??
    vision.find((v) => displayableFrameSrc(v.frameUri)) ??
    null;

  const latestRadio = radio[0] ?? null;
  const sensorReadings = (watch?.last?.sensors?.readings || []) as SensorReading[];
  const lelReading =
    sensorReadings.find((r) => (r.kind || '').toLowerCase().includes('lel')) ??
    sensorReadings[0] ??
    null;
  const coReading =
    sensorReadings.find((r) => (r.kind || '').toLowerCase().includes('co')) ?? null;
  const factor = watch?.last?.sensors?.factor;
  const showHandoff =
    demoRunning &&
    ((watch?.counts?.findingsPersisted ?? 0) > 0 ||
      (compoundFinding != null && isCompoundFinding(compoundFinding)));

  const handoffFinding =
    compoundFinding && isCompoundFinding(compoundFinding)
      ? compoundFinding
      : compoundFinding;

  return (
    <section
      className={clsx(
        'border border-line rounded-md bg-panel overflow-hidden shrink-0 flex flex-col',
        className,
      )}
      aria-label="Live Ops — cameras, radio, and sensors"
    >
      {/* Header + coach */}
      <div className="px-4 py-3 border-b border-line flex flex-col gap-2">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex flex-col gap-0.5">
            <span className="text-micro font-mono uppercase tracking-[0.12em] text-ink-dim">
              Live Ops
            </span>
            <h2 className="text-sm font-semibold text-ink leading-snug truncate">
              {demoRunning
                ? watch?.scenarioName || 'Meridian Process Unit · demo drill'
                : 'Meridian Process Unit'}
            </h2>
            <p className="text-xs text-ink-dim leading-relaxed max-w-xl">
              {demoRunning
                ? watch?.coach || 'Watching sensors, radio, and cameras together.'
                : 'Start the drill to watch sensors, radio, and cameras converge — findings come from live fusion, not the UI.'}
            </p>
          </div>
          <button
            type="button"
            onClick={() => void toggleDemo()}
            disabled={watchBusy}
            className={clsx(
              'shrink-0 inline-flex items-center gap-2 h-9 px-3.5 rounded-sm border text-xs font-medium transition-colors',
              demoRunning
                ? 'border-ok/40 text-ok bg-ok/10 hover:bg-ok/15'
                : 'border-ink/25 text-ink bg-bg hover:border-ink/40',
              watchBusy && 'opacity-60 cursor-wait',
            )}
          >
            <Activity className={clsx('h-3.5 w-3.5', demoRunning && 'animate-pulse')} />
            {demoRunning ? 'Stop demo' : 'Initiate demo'}
          </button>
        </div>

        {demoRunning && (
          <div className="flex flex-col gap-1.5 pt-1">
            <div className="flex items-baseline gap-2 min-w-0">
              <span className="text-micro font-mono uppercase tracking-[0.1em] text-watch shrink-0">
                Phase · {watch?.phaseLabel || '—'}
              </span>
              <span className="text-xs text-ink truncate">
                {watch?.phaseHint || 'Listening across streams…'}
              </span>
            </div>
            {watch?.phases && watch.phases.length > 0 && (
              <ol className="flex flex-wrap gap-x-3 gap-y-1" aria-label="Demo phases">
                {watch.phases.map((p) => (
                  <li
                    key={p.id}
                    className={clsx(
                      'text-micro font-mono uppercase tracking-[0.08em]',
                      p.active ? 'text-ink' : 'text-ink-dim/60',
                    )}
                  >
                    <span aria-hidden="true">{p.active ? '●' : '○'}</span> {p.label}
                  </li>
                ))}
              </ol>
            )}
          </div>
        )}
      </div>

      {/* Three legs */}
      <div className="grid grid-cols-1 md:grid-cols-3 min-h-[200px] max-h-[260px] divide-y md:divide-y-0 md:divide-x divide-line">
        {/* Cameras */}
        <div className="flex flex-col min-h-0 bg-bg/30">
          <div className="px-3 py-1.5 flex items-center gap-1.5 text-micro font-mono uppercase tracking-[0.08em] text-ink-dim shrink-0">
            <Camera className="h-3 w-3" />
            Cameras
          </div>
          <div className="flex-1 min-h-0 p-2">
            {camErr ? (
              <div className="h-full flex items-center justify-center px-3 text-center">
                <span className="text-xs text-ink-dim">{camErr}</span>
              </div>
            ) : !primaryCam ? (
              <div className="h-full flex flex-col items-center justify-center gap-1 px-3 text-center">
                <span className="text-xs text-ink-dim">Demo camera · waiting for frames</span>
                {latestDetection && displayableFrameSrc(latestDetection.frameUri) && (
                  <img
                    src={displayableFrameSrc(latestDetection.frameUri)!}
                    alt="Last detection still"
                    className="mt-1 max-h-20 border border-line object-contain"
                  />
                )}
              </div>
            ) : (
              <div className="h-full relative border border-line bg-ink/5 overflow-hidden">
                <img
                  src={primaryCam.streamPath || primaryCam.snapshotPath || ''}
                  alt={`${primaryCam.cameraId} live`}
                  className="absolute inset-0 w-full h-full object-cover opacity-95"
                />
                <span className="absolute bottom-0 inset-x-0 px-1.5 py-0.5 bg-ink/70 text-micro font-mono text-panel truncate">
                  {primaryCam.cameraId} · {primaryCam.zoneId}
                  {primaryCam.sourceKind === 'demo' ? ' · DEMO' : ' · LIVE'}
                  {latestDetection ? ` · ${latestDetection.label}` : ''}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Radio */}
        <div className="flex flex-col min-h-0">
          <div className="px-3 py-1.5 flex items-center gap-1.5 text-micro font-mono uppercase tracking-[0.08em] text-ink-dim shrink-0">
            <Radio className="h-3 w-3" />
            Radio
          </div>
          <div className="flex-1 min-h-0 overflow-y-auto scrollbar px-3 pb-2">
            {voiceErr && radio.length === 0 ? (
              <span className="text-xs text-ink-dim">{voiceErr}</span>
            ) : !latestRadio ? (
              <div className="flex flex-col gap-1 py-3">
                <span className="text-xs text-ink-dim">Quiet</span>
                <span className="text-micro text-ink-dim/70">
                  Radio lines appear as the drill advances
                </span>
              </div>
            ) : (
              <div className="py-2 flex flex-col gap-2">
                <p className="text-xs text-ink leading-snug">
                  <span className="font-mono text-ink-dim mr-1.5">
                    {latestRadio.zoneId || '—'}
                  </span>
                  {latestRadio.transcript || '(empty transcript)'}
                </p>
                {displayableAudioSrc(latestRadio.audioClipUri) && (
                  <audio
                    controls
                    preload="none"
                    src={displayableAudioSrc(latestRadio.audioClipUri)!}
                    className="w-full h-7"
                    onPlay={() => setPlayingId(latestRadio.eventId)}
                    onPause={() =>
                      setPlayingId((id) => (id === latestRadio.eventId ? null : id))
                    }
                    data-playing={playingId === latestRadio.eventId ? '1' : '0'}
                  />
                )}
                {radio.length > 1 && (
                  <span className="text-micro font-mono text-ink-dim">
                    +{radio.length - 1} earlier
                  </span>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Sensors */}
        <div className="flex flex-col min-h-0 bg-bg/20">
          <div className="px-3 py-1.5 flex items-center gap-1.5 text-micro font-mono uppercase tracking-[0.08em] text-ink-dim shrink-0">
            <Gauge className="h-3 w-3" />
            Sensors
          </div>
          <div className="flex-1 min-h-0 px-3 py-2 flex flex-col gap-2">
            {!demoRunning && !lelReading ? (
              <div className="flex flex-col gap-1 py-2">
                <span className="text-xs text-ink-dim">Idle</span>
                <span className="text-micro text-ink-dim/70">
                  LEL and gas readings publish when the drill runs
                </span>
              </div>
            ) : (
              <>
                <div className="flex flex-col gap-0.5">
                  <span className="text-micro font-mono uppercase tracking-[0.08em] text-ink-dim">
                    LEL · {lelReading?.zoneId || watch?.zonePrimary || 'B-04'}
                  </span>
                  <span className="text-lg font-semibold tabular-nums text-ink font-mono">
                    {lelReading?.value != null ? lelReading.value.toFixed(1) : '—'}
                    <span className="text-xs font-normal text-ink-dim ml-1">
                      {lelReading?.unit || '%LEL'}
                    </span>
                  </span>
                  <span className="text-xs text-ink-dim">{underAlarmLabel(factor)}</span>
                </div>
                {coReading && (
                  <div className="pt-1 border-t border-line/60">
                    <span className="text-micro font-mono text-ink-dim">
                      CO · {coReading.zoneId || '—'}
                    </span>
                    <div className="text-sm font-mono tabular-nums text-ink">
                      {coReading.value?.toFixed(1)} {coReading.unit || 'ppm'}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Finding handoff */}
      {showHandoff && handoffFinding ? (
        <Link
          to={`/findings/${handoffFinding.findingId}`}
          className="h-10 px-4 border-t border-accent/30 bg-accent/8 flex items-center justify-between gap-3 text-sm text-ink hover:bg-accent/12 transition-colors"
        >
          <span className="truncate font-medium">
            Open compound finding
            <span className="text-ink-dim font-normal ml-2 text-xs">
              {handoffFinding.zoneId} · {handoffFinding.leadTimeBand}
            </span>
          </span>
          <ArrowRight className="h-4 w-4 shrink-0 text-accent" />
        </Link>
      ) : (
        <div className="h-8 px-4 border-t border-line flex items-center text-micro font-mono text-ink-dim bg-panel-2/40">
          {demoRunning
            ? 'Waiting for fusion to open a compound finding…'
            : 'Initiate demo to start the multi-source drill'}
        </div>
      )}
    </section>
  );
}
