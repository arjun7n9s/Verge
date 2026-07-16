import { useCallback, useEffect, useRef, useState } from 'react';
import { useFindingsStore, useFilteredFindings } from '@/stores/findings';
import { FindingsBoard } from '@/components/organisms/FindingsBoard';
import { FindingFilters } from '@/components/molecules/FindingFilters';
import { SuppressionSuggestion } from '@/components/organisms/SuppressionSuggestion';
import { ResponseOrchestratorPanel } from '@/components/organisms/ResponseOrchestratorPanel';
import { EmergencyPanel } from '@/components/organisms/EmergencyPanel';
import { FindingCardSkeleton } from '@/components/atoms';
import { PanelSystem } from '@/components/organisms/PanelSystem';
import { getFindings } from '@/api';
import { useFindingsStream } from '@/hooks/useFindingsStream';
import { MobileNavigation } from '@/components/organisms/MobileNavigation';
import { FindingCardMobile } from '@/components/organisms/FindingCardMobile';
import { MobileFieldWorkerPanel } from '@/components/organisms/MobileFieldWorkerPanel';
import { PermitsPanel } from '@/components/organisms/PermitsPanel';
import { DigitalTwinMap } from '@/components/organisms/DigitalTwinMap';
import { AlertCircle } from 'lucide-react';

export default function FindingsView() {
  const { setFindings, setLoading, setError, isLoading, error, shadow, findings } = useFindingsStore();
  const filteredFindings = useFilteredFindings();

  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  const [mobileTab, setMobileTab] = useState<'home' | 'map' | 'permits' | 'profile'>('home');
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const loadDataRef = useRef<() => Promise<void>>(async () => {});

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
      <div className="flex flex-col h-[calc(100vh-120px)] overflow-hidden relative text-ink">
        {error && mobileTab === 'home' && (
          <div className="bg-imminent/10 border-b border-imminent/20 text-imminent text-[10px] p-2 flex items-center gap-2 select-text shrink-0 font-mono uppercase">
            <AlertCircle className="h-3.5 w-3.5 shrink-0 text-imminent" />
            <div className="flex-1">Backend offline — no live findings available.</div>
          </div>
        )}

        <div className="flex-1 overflow-y-auto scrollbar p-4 pb-2">
          {mobileTab === 'home' && (
            <div className="flex flex-col gap-3">
              <span className="text-xs font-mono font-bold text-ink-dim uppercase select-none">
                Active Field Findings
              </span>
              {filteredFindings.map((finding) => (
                <FindingCardMobile key={finding.findingId} finding={finding} onChange={loadData} />
              ))}
              {filteredFindings.length === 0 && (
                <div className="text-center p-6 border border-dashed border-line text-xs font-mono text-ink-dim uppercase rounded">
                  NO ACTIVE ALARMS
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
    <div className="flex flex-col gap-4 p-4 h-[calc(100vh-80px)] overflow-hidden">
      {error && (
        <div className="bg-imminent/10 border border-imminent/20 text-imminent text-xs rounded p-2.5 flex items-center gap-2 select-text shrink-0">
          <AlertCircle className="h-4 w-4 shrink-0 text-imminent" />
          <div className="flex-1">
            <span className="font-bold uppercase tracking-wider mr-1">BACKEND OFFLINE:</span>
            {error}
          </div>
        </div>
      )}

      <div className="flex items-center justify-between border-b border-line pb-3 shrink-0">
        <FindingFilters />
        <div className="text-xs text-ink-dim tabular-nums">
          Showing <span className="font-semibold text-ink">{filteredFindings.length}</span> findings
        </div>
      </div>

      <div className="flex-1 overflow-hidden flex flex-col gap-3 relative">
        <SuppressionSuggestion activeFindings={findings} onChange={loadData} />

        {isLoading && findings.length === 0 ? (
          <div className="flex gap-3 h-full px-1" aria-label="Loading findings">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex-1 flex flex-col gap-2 bg-panel/30 border border-line rounded-md p-2">
                <FindingCardSkeleton />
                {i % 2 === 0 && <FindingCardSkeleton />}
              </div>
            ))}
          </div>
        ) : (
          <PanelSystem
            findings={filteredFindings}
            boardComponent={<FindingsBoard findings={filteredFindings} onChange={loadData} />}
            responseComponent={
              <div className="flex flex-col gap-3">
                <EmergencyPanel activeFindings={findings} onChange={loadData} />
                <ResponseOrchestratorPanel activeFindings={findings} onChange={loadData} />
              </div>
            }
          />
        )}
      </div>
    </div>
  );
}
