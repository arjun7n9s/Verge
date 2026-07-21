import { useCallback, useEffect, useRef, useState } from 'react';
import { useFindingsStore, useFilteredFindings } from '@/stores/findings';
import { FindingsBoard } from '@/components/organisms/FindingsBoard';
import { FindingsBandList } from '@/components/organisms/FindingsBandList';
import { LiveOpsStage } from '@/components/organisms/LiveOpsStage';
import { FindingFilters } from '@/components/molecules/FindingFilters';
import { SuppressionSuggestion } from '@/components/organisms/SuppressionSuggestion';
import { ResponseOrchestratorPanel } from '@/components/organisms/ResponseOrchestratorPanel';
import { EmergencyPanel } from '@/components/organisms/EmergencyPanel';
import { FindingCardSkeleton } from '@/components/atoms';
import { ErrorBoundary } from '@/components/atoms/ErrorBoundary';
import { getFindings } from '@/api';
import { useFindingsStream } from '@/hooks/useFindingsStream';
import { MobileNavigation } from '@/components/organisms/MobileNavigation';
import { FindingCardMobile } from '@/components/organisms/FindingCardMobile';
import { MobileFieldWorkerPanel } from '@/components/organisms/MobileFieldWorkerPanel';
import { PermitsPanel } from '@/components/organisms/PermitsPanel';
import { DigitalTwinMap } from '@/components/organisms/DigitalTwinMap';
import { AlertCircle, Map, Siren, X, LayoutList, Columns3 } from 'lucide-react';
import clsx from 'clsx';

/* ── Board — Live Risk triage (design_plan §6.1) ─────────────────────
   First viewport: Live Ops stage (always on). Then filters + band-first
   triage (default); column kanban as a toggle. Map/Response stay rails. */

type Rail = 'map' | 'response' | null;
type TriageMode = 'band' | 'columns';

export default function FindingsView() {
  const { setFindings, setLoading, setError, isLoading, error, shadow, findings } = useFindingsStore();
  const filteredFindings = useFilteredFindings();

  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  const [mobileTab, setMobileTab] = useState<'home' | 'map' | 'permits' | 'profile'>('home');
  const [rail, setRail] = useState<Rail>(null);
  const [triageMode, setTriageMode] = useState<TriageMode>('band');
  const [demoRunning, setDemoRunning] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const loadDataRef = useRef<() => Promise<void>>(async () => {});

  const onDemoChange = useCallback((running: boolean) => {
    setDemoRunning(running);
    if (running) setRail(null);
  }, []);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback(() => {
    if (pollRef.current) return;
    pollRef.current = setInterval(() => {
      void loadDataRef.current();
    }, 5000);
  }, []);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getFindings(shadow);
      setFindings(data);
      setError(null);
    } catch {
      setError('API gateway offline. Start the backend with `make dev`.');
      setFindings([]);
    } finally {
      setLoading(false);
    }
  }, [shadow, setFindings, setLoading, setError]);

  loadDataRef.current = loadData;

  const onStreamFindings = useCallback(
    (data: Parameters<typeof setFindings>[0]) => {
      stopPolling();
      setFindings(data);
      setError(null);
    },
    [setFindings, setError, stopPolling],
  );

  const onStreamError = useCallback(() => {
    startPolling();
  }, [startPolling]);

  useFindingsStream(!shadow, onStreamFindings, onStreamError);

  useEffect(() => {
    stopPolling();
    void loadData();
    if (shadow) {
      startPolling();
    }
    return stopPolling;
  }, [shadow, loadData, startPolling, stopPolling]);

  if (isMobile) {
    return (
      <div className="flex flex-col h-full overflow-hidden relative text-ink">
        {error && mobileTab === 'home' && (
          <div className="bg-imminent/10 border-b border-imminent/20 p-2 flex items-baseline gap-2 select-text shrink-0">
            <AlertCircle className="h-3.5 w-3.5 shrink-0 self-center text-imminent" />
            <span className="text-micro font-mono uppercase tracking-[0.08em] text-imminent font-semibold shrink-0">
              Offline
            </span>
            <span className="text-micro text-ink flex-1">No live findings available.</span>
          </div>
        )}

        <div className="flex-1 overflow-y-auto scrollbar p-4 pb-16">
          {mobileTab === 'home' && (
            <div className="flex flex-col gap-3">
              <LiveOpsStage onDemoChange={onDemoChange} />
              <span className="ruled-label">Active field findings</span>
              {filteredFindings.map((finding) => (
                <FindingCardMobile key={finding.findingId} finding={finding} onChange={loadData} />
              ))}
              {filteredFindings.length === 0 && (
                <div className="text-center p-6 border border-dashed border-line rounded-md flex flex-col gap-1">
                  <span className="text-xs font-medium text-ink-dim">No findings in the field</span>
                  <span className="text-micro font-mono text-ink-dim/60">
                    New risks will appear here with their lead-time band.
                  </span>
                </div>
              )}
            </div>
          )}

          {mobileTab === 'map' && (
            <div className="h-full min-h-[300px] w-full">
              <DigitalTwinMap findings={filteredFindings} />
            </div>
          )}

          {mobileTab === 'permits' && (
            <div className="h-full">
              <PermitsPanel />
            </div>
          )}

          {mobileTab === 'profile' && <MobileFieldWorkerPanel findings={filteredFindings} />}
        </div>

        <MobileNavigation activeTab={mobileTab} setActiveTab={setMobileTab} />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 p-4 h-full overflow-hidden">
      {error && (
        <div className="bg-imminent/10 border border-imminent/20 rounded p-2.5 flex items-baseline gap-2 select-text shrink-0">
          <AlertCircle className="h-4 w-4 shrink-0 self-center text-imminent" />
          <span className="text-micro font-mono uppercase tracking-[0.08em] text-imminent font-semibold shrink-0">
            Backend offline
          </span>
          <span className="text-xs text-ink flex-1">{error}</span>
        </div>
      )}

      {/* Live Ops — mandatory presence; never hidden when quiet */}
      <LiveOpsStage onDemoChange={onDemoChange} />

      {/* Triage — secondary during demo drill */}
      <div
        className={clsx(
          'flex items-center justify-between gap-4 border-b border-line pb-3 shrink-0',
          demoRunning && 'opacity-80',
        )}
      >
        <div className="flex items-center gap-3 min-w-0">
          {demoRunning && (
            <span className="ruled-label shrink-0 !mb-0">Triage</span>
          )}
          <FindingFilters />
        </div>
        {!demoRunning && (
          <div className="flex items-center gap-3 shrink-0">
            <span className="text-xs text-ink-dim tabular-nums hidden xl:inline">
              Showing <span className="font-semibold text-ink">{filteredFindings.length}</span>{' '}
              findings
            </span>
            <div className="flex bg-panel-2 border border-line p-0.5 rounded" role="group" aria-label="Triage layout">
              <button
                onClick={() => setTriageMode('band')}
                aria-pressed={triageMode === 'band'}
                className={clsx(
                  'flex items-center gap-1.5 h-6 px-2.5 text-micro font-mono font-bold uppercase rounded-sm transition-colors duration-fast cursor-pointer',
                  triageMode === 'band' ? 'bg-panel text-ink border border-line' : 'text-ink-dim hover:text-ink',
                )}
              >
                <LayoutList className="h-3 w-3" />
                Band
              </button>
              <button
                onClick={() => setTriageMode('columns')}
                aria-pressed={triageMode === 'columns'}
                className={clsx(
                  'flex items-center gap-1.5 h-6 px-2.5 text-micro font-mono font-bold uppercase rounded-sm transition-colors duration-fast cursor-pointer',
                  triageMode === 'columns' ? 'bg-panel text-ink border border-line' : 'text-ink-dim hover:text-ink',
                )}
              >
                <Columns3 className="h-3 w-3" />
                Columns
              </button>
            </div>
            <div className="flex bg-panel-2 border border-line p-0.5 rounded" role="group" aria-label="Side rail">
              <button
                onClick={() => setRail(rail === 'map' ? null : 'map')}
                aria-pressed={rail === 'map'}
                className={clsx(
                  'flex items-center gap-1.5 h-6 px-2.5 text-micro font-mono font-bold uppercase rounded-sm transition-colors duration-fast cursor-pointer',
                  rail === 'map' ? 'bg-panel text-ink border border-line' : 'text-ink-dim hover:text-ink',
                )}
              >
                <Map className="h-3 w-3" />
                Map
              </button>
              <button
                onClick={() => setRail(rail === 'response' ? null : 'response')}
                aria-pressed={rail === 'response'}
                className={clsx(
                  'flex items-center gap-1.5 h-6 px-2.5 text-micro font-mono font-bold uppercase rounded-sm transition-colors duration-fast cursor-pointer',
                  rail === 'response' ? 'bg-panel text-ink border border-line' : 'text-ink-dim hover:text-ink',
                )}
              >
                <Siren className="h-3 w-3" />
                Response
              </button>
            </div>
          </div>
        )}
      </div>

      <div
        className={clsx(
          'flex-1 overflow-hidden flex flex-col gap-3 relative min-h-0',
          demoRunning && 'max-h-[40vh]',
        )}
      >
        {!demoRunning && (
          <SuppressionSuggestion activeFindings={findings} onChange={loadData} />
        )}

        {isLoading && findings.length === 0 ? (
          <div className="flex flex-col gap-2 max-w-3xl" aria-label="Loading findings">
            <FindingCardSkeleton />
            <FindingCardSkeleton />
            <FindingCardSkeleton />
          </div>
        ) : (
          <div
            className={clsx(
              'flex-1 min-h-0 grid gap-4',
              (rail === null || demoRunning) && 'grid-cols-1',
              !demoRunning && rail === 'map' && 'grid-cols-[minmax(0,1fr)_440px]',
              !demoRunning && rail === 'response' && 'grid-cols-[minmax(0,1fr)_380px]',
            )}
          >
            <div className="min-w-0 min-h-0 overflow-hidden">
              {demoRunning || triageMode === 'band' ? (
                <FindingsBandList findings={filteredFindings} onChange={loadData} />
              ) : (
                <FindingsBoard findings={filteredFindings} onChange={loadData} />
              )}
            </div>

            {!demoRunning && rail !== null && (
              <aside className="surface-1 bg-panel min-h-0 flex flex-col overflow-hidden">
                <div className="h-8 border-b border-line flex items-center justify-between px-3 shrink-0">
                  <span className="text-micro font-mono uppercase tracking-[0.12em] text-ink-dim select-none">
                    {rail === 'map' ? 'Plant map · digital twin' : 'Emergency response'}
                  </span>
                  <button
                    onClick={() => setRail(null)}
                    aria-label="Close rail"
                    className="text-ink-dim hover:text-ink transition-colors duration-fast cursor-pointer"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
                <div className="flex-1 min-h-0 overflow-hidden">
                  {rail === 'map' ? (
                    <ErrorBoundary>
                      <DigitalTwinMap findings={filteredFindings} />
                    </ErrorBoundary>
                  ) : (
                    <div className="h-full overflow-y-auto scrollbar p-3 flex flex-col gap-3">
                      <ErrorBoundary>
                        <EmergencyPanel activeFindings={findings} onChange={loadData} />
                        <ResponseOrchestratorPanel activeFindings={findings} onChange={loadData} />
                      </ErrorBoundary>
                    </div>
                  )}
                </div>
              </aside>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
