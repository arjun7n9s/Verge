/**
 * Live Ops stage — persistent Board presence (design_plan §6.1).
 * Multi-cam wall + radio with optional clip playback. Never returns null.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Radio, Camera, BookMarked, LayoutGrid, Activity } from 'lucide-react';
import { useAuthStore } from '@/stores/auth';
import { useFindingsStore } from '@/stores/findings';
import { BAND_SEVERITY } from '@/types';
import {
  displayableAudioSrc,
  displayableFrameSrc,
  fetchCameras,
  fetchProactiveLessons,
  fetchVisionEvents,
  fetchVoiceEvents,
  type CameraRow,
  type LessonCardRow,
  type VisionDetectionRow,
  type VoiceEventRow,
} from '@/api/liveOps';
import { fetchWatchStatus, startWatch, stopWatch, type WatchStatus } from '@/api/watch';
import clsx from 'clsx';

const RADIO_ROLES = new Set(['Safety_Engineer', 'administrator']);

type ViewMode = 'wall' | 'focus';

export function LiveOpsStage({ className }: { className?: string }) {
  const user = useAuthStore((s) => s.user);
  const roles = user?.roles ?? [];
  const radioAllowed = !user || roles.some((r) => RADIO_ROLES.has(r));

  const findings = useFindingsStore((s) => s.findings);
  const focusFinding = useMemo(
    () =>
      [...findings]
        .filter((f) => f.state !== 'closed' && f.state !== 'resolved')
        .sort((a, b) => BAND_SEVERITY[a.leadTimeBand] - BAND_SEVERITY[b.leadTimeBand])[0],
    [findings],
  );
  const focusZone = focusFinding?.zoneId;

  const [radio, setRadio] = useState<VoiceEventRow[]>([]);
  const [vision, setVision] = useState<VisionDetectionRow[]>([]);
  const [cameras, setCameras] = useState<CameraRow[]>([]);
  const [lesson, setLesson] = useState<LessonCardRow | null>(null);
  const [voiceErr, setVoiceErr] = useState<string | null>(null);
  const [camErr, setCamErr] = useState<string | null>(null);
  const [selectedCam, setSelectedCam] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('wall');
  const [playingId, setPlayingId] = useState<string | null>(null);
  const [watch, setWatch] = useState<WatchStatus | null>(null);
  const [watchBusy, setWatchBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const pollWatch = async () => {
      try {
        const s = await fetchWatchStatus();
        if (!cancelled) setWatch(s);
      } catch {
        if (!cancelled) setWatch(null);
      }
    };
    void pollWatch();
    const id = setInterval(() => void pollWatch(), 2000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const toggleWatch = async () => {
    setWatchBusy(true);
    try {
      const s = watch?.running ? await stopWatch() : await startWatch({ intervalS: 3 });
      setWatch(s);
    } catch {
      /* status poll will refresh */
    } finally {
      setWatchBusy(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      if (radioAllowed) {
        try {
          const events = await fetchVoiceEvents(10);
          if (!cancelled) {
            setRadio(events);
            setVoiceErr(null);
          }
        } catch {
          if (!cancelled) {
            setRadio([]);
            setVoiceErr('radio feed offline');
          }
        }
      } else {
        setRadio([]);
        setVoiceErr(null);
      }

      try {
        const [dets, cams] = await Promise.all([fetchVisionEvents(10), fetchCameras()]);
        if (!cancelled) {
          setVision(dets);
          setCameras(cams);
          setCamErr(null);
          setSelectedCam((prev) => {
            if (prev && cams.some((c) => c.cameraId === prev)) return prev;
            const zoneMatch = focusZone
              ? cams.find((c) => c.zoneId === focusZone && c.hasSource)
              : undefined;
            return (zoneMatch ?? cams.find((c) => c.hasSource) ?? cams[0])?.cameraId ?? null;
          });
        }
      } catch {
        if (!cancelled) {
          setVision([]);
          setCameras([]);
          setCamErr('camera feed offline');
        }
      }

      if (focusZone) {
        try {
          const cards = await fetchProactiveLessons(focusZone);
          if (!cancelled) setLesson(cards[0] ?? null);
        } catch {
          if (!cancelled) setLesson(null);
        }
      } else if (!cancelled) {
        setLesson(null);
      }
    };
    void load();
    const id = setInterval(() => void load(), 8000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [radioAllowed, focusZone]);

  const liveCams = cameras.filter((c) => c.hasSource);
  const focusCam =
    liveCams.find((c) => c.cameraId === selectedCam) ??
    liveCams.find((c) => c.zoneId === focusZone) ??
    liveCams[0] ??
    null;

  const latestWithFrame = vision.find((v) => displayableFrameSrc(v.frameUri));
  const detectionOverlay =
    (focusCam &&
      vision.find(
        (v) => v.cameraId === focusCam.cameraId && displayableFrameSrc(v.frameUri),
      )) ??
    latestWithFrame ??
    null;

  return (
    <section
      className={clsx(
        'border border-line rounded-md bg-panel overflow-hidden shrink-0 flex flex-col',
        className,
      )}
      aria-label="Live Ops — cameras and radio"
    >
      <div className="h-8 px-3 border-b border-line flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-micro font-mono uppercase tracking-[0.12em] text-ink-dim">
            Live Ops
          </span>
          <button
            type="button"
            onClick={() => void toggleWatch()}
            disabled={watchBusy}
            className={clsx(
              'inline-flex items-center gap-1 px-1.5 py-0.5 rounded-sm border text-micro font-mono uppercase tracking-[0.08em] transition-colors',
              watch?.running
                ? 'border-ok/40 text-ok bg-ok/10'
                : 'border-line text-ink-dim hover:text-ink hover:border-ink/30',
              watchBusy && 'opacity-60 cursor-wait',
            )}
            title={
              watch?.running
                ? 'Stop continuous watch (vision + radio + sensors → fusion → memory)'
                : 'Start continuous watch — real pipelines, not hardcoded UI'
            }
          >
            <Activity className={clsx('h-3 w-3', watch?.running && 'animate-pulse')} />
            {watch?.running ? 'Watch on' : 'Watch off'}
          </button>
          {watch?.running && (
            <span className="text-micro font-mono text-ink-dim tabular-nums truncate">
              tick {watch.ticks}
              {watch.counts?.visionDetections != null && (
                <> · v {watch.counts.visionDetections}</>
              )}
              {watch.counts?.voiceEvents != null && watch.counts.voiceEvents > 0 && (
                <> · r {watch.counts.voiceEvents}</>
              )}
              {watch.counts?.findingsPersisted != null &&
                watch.counts.findingsPersisted > 0 && (
                  <> · f {watch.counts.findingsPersisted}</>
                )}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 text-micro font-mono text-ink-dim tabular-nums">
          <span>Cams · {liveCams.length || cameras.length}</span>
          <span>Radio · {radioAllowed ? radio.length : '—'}</span>
          {lesson && (
            <span className="text-watch truncate max-w-[160px]" title={lesson.title}>
              Lesson · {lesson.lessonId}
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)] min-h-[200px] max-h-[280px]">
        {/* Camera wall / focus */}
        <div className="border-b md:border-b-0 md:border-r border-line flex flex-col min-h-0 bg-bg/40">
          <div className="px-3 py-1.5 flex items-center gap-2 text-micro font-mono uppercase tracking-[0.08em] text-ink-dim shrink-0">
            <Camera className="h-3 w-3" />
            Cameras
            <div className="ml-auto flex items-center gap-1 normal-case tracking-normal">
              <button
                type="button"
                onClick={() => setViewMode('wall')}
                className={clsx(
                  'px-1.5 py-0.5 rounded-sm border text-micro',
                  viewMode === 'wall'
                    ? 'border-ink/30 text-ink bg-bg'
                    : 'border-transparent text-ink-dim hover:text-ink',
                )}
                title="Multi-cam wall"
              >
                <LayoutGrid className="h-3 w-3 inline mr-0.5" />
                Wall
              </button>
              <button
                type="button"
                onClick={() => setViewMode('focus')}
                className={clsx(
                  'px-1.5 py-0.5 rounded-sm border text-micro',
                  viewMode === 'focus'
                    ? 'border-ink/30 text-ink bg-bg'
                    : 'border-transparent text-ink-dim hover:text-ink',
                )}
              >
                Focus
              </button>
            </div>
          </div>

          {cameras.length > 0 && (
            <div className="px-2 pb-1 flex flex-wrap gap-1 shrink-0">
              {cameras.map((c) => (
                <button
                  key={c.cameraId}
                  type="button"
                  onClick={() => {
                    setSelectedCam(c.cameraId);
                    setViewMode('focus');
                  }}
                  className={clsx(
                    'px-1.5 py-0.5 text-micro font-mono rounded-sm border transition-colors',
                    selectedCam === c.cameraId
                      ? 'border-ink/40 text-ink bg-bg'
                      : 'border-line text-ink-dim hover:text-ink',
                    !c.hasSource && 'opacity-50',
                  )}
                >
                  {c.cameraId}
                  <span className="text-ink-dim/70 ml-1">{c.zoneId}</span>
                </button>
              ))}
            </div>
          )}

          <div className="flex-1 min-h-0 p-2">
            {camErr ? (
              <div className="h-full flex items-center justify-center">
                <span className="text-xs text-ink-dim font-mono px-3 text-center">{camErr}</span>
              </div>
            ) : liveCams.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center gap-1 px-4 text-center">
                <span className="text-xs text-ink-dim">No camera sources configured</span>
                <span className="text-micro font-mono text-ink-dim/70">
                  Set registry source or VERGE_VISION_RTSP_URL
                </span>
                {detectionOverlay && displayableFrameSrc(detectionOverlay.frameUri) && (
                  <img
                    src={displayableFrameSrc(detectionOverlay.frameUri)!}
                    alt="Last detection still"
                    className="mt-2 max-h-24 border border-line object-contain"
                  />
                )}
              </div>
            ) : viewMode === 'wall' ? (
              <div
                className={clsx(
                  'h-full grid gap-1.5',
                  liveCams.length === 1 && 'grid-cols-1',
                  liveCams.length === 2 && 'grid-cols-2',
                  liveCams.length >= 3 && 'grid-cols-2',
                )}
              >
                {liveCams.slice(0, 4).map((c) => (
                  <button
                    key={c.cameraId}
                    type="button"
                    onClick={() => {
                      setSelectedCam(c.cameraId);
                      setViewMode('focus');
                    }}
                    className="relative border border-line bg-ink/5 overflow-hidden min-h-[72px] group"
                  >
                    <img
                      src={c.streamPath || c.snapshotPath || ''}
                      alt={`${c.cameraId} live`}
                      className="absolute inset-0 w-full h-full object-cover opacity-90 group-hover:opacity-100"
                    />
                    <span className="absolute bottom-0 inset-x-0 px-1.5 py-0.5 bg-ink/70 text-micro font-mono text-panel truncate text-left">
                      {c.cameraId} · {c.zoneId}
                      {c.sourceKind === 'demo' ? ' · DEMO' : ''}
                    </span>
                  </button>
                ))}
              </div>
            ) : focusCam ? (
              <div className="h-full relative border border-line bg-ink/5 overflow-hidden">
                <img
                  src={focusCam.streamPath || focusCam.snapshotPath || ''}
                  alt={`${focusCam.cameraId} live stream`}
                  className="absolute inset-0 w-full h-full object-contain"
                />
                <div className="absolute top-1 left-1 right-1 flex justify-between gap-2 pointer-events-none">
                  <span className="px-1.5 py-0.5 bg-ink/70 text-micro font-mono text-panel">
                    {focusCam.cameraId} · {focusCam.zoneId}
                    {focusCam.sourceKind === 'demo' ? ' · DEMO' : ' · LIVE'}
                  </span>
                  {detectionOverlay && (
                    <span className="px-1.5 py-0.5 bg-ink/70 text-micro font-mono text-panel truncate">
                      Last detect · {detectionOverlay.label}
                    </span>
                  )}
                </div>
              </div>
            ) : null}
          </div>
        </div>

        {/* Radio rail */}
        <div className="flex flex-col min-h-0 min-w-0">
          <div className="px-3 py-1.5 flex items-center gap-1.5 text-micro font-mono uppercase tracking-[0.08em] text-ink-dim shrink-0">
            <Radio className="h-3 w-3" />
            Radio
          </div>
          <div className="flex-1 min-h-0 overflow-y-auto scrollbar px-3 pb-2">
            {!radioAllowed ? (
              <span className="text-xs text-ink-dim">Radio restricted to Safety Engineer</span>
            ) : voiceErr ? (
              <span className="text-xs text-ink-dim font-mono">{voiceErr}</span>
            ) : radio.length === 0 ? (
              <div className="flex flex-col gap-1 py-2">
                <span className="text-xs text-ink-dim">No recent radio events</span>
                <span className="text-micro font-mono text-ink-dim/70">
                  Transcripts + clips appear when voice events arrive
                </span>
              </div>
            ) : (
              <ul className="flex flex-col gap-2 py-1">
                {radio.slice(0, 6).map((ev) => {
                  const audioSrc = displayableAudioSrc(ev.audioClipUri);
                  return (
                    <li
                      key={ev.eventId}
                      className="text-xs leading-snug border-b border-line/50 pb-1.5 last:border-0"
                    >
                      <div className="flex items-start gap-2">
                        <span className="font-mono text-ink-dim shrink-0">
                          {ev.zoneId || '—'}
                        </span>
                        <span className="text-ink flex-1 min-w-0">
                          {ev.transcript || '(empty transcript)'}
                        </span>
                      </div>
                      {audioSrc && (
                        <audio
                          controls
                          preload="none"
                          src={audioSrc}
                          className="mt-1 w-full h-7"
                          onPlay={() => setPlayingId(ev.eventId)}
                          onPause={() =>
                            setPlayingId((id) => (id === ev.eventId ? null : id))
                          }
                          data-playing={playingId === ev.eventId ? '1' : '0'}
                        />
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      </div>

      <div className="h-7 px-3 border-t border-line flex items-center gap-3 text-micro font-mono text-ink-dim bg-panel-2/40">
        {focusFinding ? (
          <Link
            to={`/findings/${focusFinding.findingId}`}
            className="hover:text-ink transition-colors truncate"
          >
            Focus · {focusFinding.findingId} · {focusFinding.leadTimeBand} · {focusFinding.zoneId}
          </Link>
        ) : (
          <span>No open finding to focus</span>
        )}
        {lesson && (
          <span className="flex items-center gap-1 truncate ml-auto text-watch">
            <BookMarked className="h-3 w-3 shrink-0" />
            {lesson.title}
          </span>
        )}
      </div>
    </section>
  );
}
