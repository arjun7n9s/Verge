import { useEffect, useState } from 'react';
import type { RiskFinding } from '@/types';
import { Modal, Button } from '@/components/atoms';
import { transitionFinding, getFindingExposure } from '@/api';
import type { FindingExposure } from '@/api/workers';
import { TemporalConvergenceChart } from './TemporalConvergenceChart';
import { LeadTimeGauge } from '@/components/molecules/LeadTimeGauge';
import { InvestigationPanel } from '@/components/molecules/InvestigationPanel';
import { ExportEvidenceButton } from '@/components/molecules/ExportEvidenceButton';
import { ExportIncidentReportButton } from '@/components/molecules/ExportIncidentReportButton';
import { FindingAuditTab } from '@/components/molecules/FindingAuditTab';
import {
  FileText,
  ShieldCheck,
  TrendingUp,
  Sliders,
  AlertTriangle,
} from 'lucide-react';
import clsx from 'clsx';

interface FindingDetailModalProps {
  finding: RiskFinding | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

type TabType = 'overview' | 'chart' | 'lineage' | 'audit';

export function FindingDetailModal({ finding, isOpen, onClose, onSuccess }: FindingDetailModalProps) {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [exposure, setExposure] = useState<FindingExposure | null>(null);

  const findingId = finding?.findingId ?? null;
  useEffect(() => {
    if (!isOpen || !findingId) return;
    let cancelled = false;
    getFindingExposure(findingId)
      .then((e) => {
        if (!cancelled) setExposure(e);
      })
      .catch(() => {
        if (!cancelled) setExposure(null);
      });
    return () => {
      cancelled = true;
    };
  }, [isOpen, findingId]);

  if (!finding) return null;

  const tabs: { value: TabType; label: string; icon: React.ReactNode }[] = [
    { value: 'overview', label: 'OVERVIEW', icon: <Sliders className="h-3.5 w-3.5" /> },
    { value: 'chart', label: 'CONVERGENCE CHART', icon: <TrendingUp className="h-3.5 w-3.5" /> },
    { value: 'lineage', label: 'EVIDENCE LINEAGE', icon: <FileText className="h-3.5 w-3.5" /> },
    { value: 'audit', label: 'AUDIT CHAIN', icon: <ShieldCheck className="h-3.5 w-3.5" /> },
  ];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Finding Details: ${finding.findingId}`}
      description={`${finding.zoneId} · Risk Finding Analysis`}
      size="xl"
    >
      <div className="flex flex-col md:flex-row gap-4 h-[500px] overflow-hidden text-ink">
        
        {/* Left column: Summary Stats Card */}
        <div className="w-full md:w-60 flex flex-col gap-3 border-r border-line pr-4 select-none">
          <div className="flex flex-col gap-1">
            <span className="text-micro font-mono text-ink-dim uppercase">Lead time to breach</span>
            <LeadTimeGauge band={finding.leadTimeBand} basis={finding.leadTimeBasis} size="md" />
          </div>

          <div className="flex flex-col gap-1 font-mono text-xs">
            <span className="text-micro text-ink-dim uppercase">State</span>
            <div className="border border-line rounded px-2.5 py-1 bg-panel-2/50 text-ink uppercase font-bold flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-accent" />
              {finding.state}
            </div>
          </div>

          <div className="flex flex-col gap-1 font-mono text-xs">
            <span className="text-micro text-ink-dim uppercase">Confidence Rating</span>
            <div className="border border-line rounded px-2.5 py-1 bg-panel-2/50 text-ink font-bold tabular-nums">
              {(finding.confidence * 100).toFixed(0)}%
            </div>
          </div>

          <div className="flex flex-col gap-1 font-mono text-xs">
            <span className="text-micro text-ink-dim uppercase">Estimate Quality</span>
            <div className="border border-line rounded px-2.5 py-1 bg-panel-2/50 text-ink uppercase">
              {finding.estimateQuality}
            </div>
          </div>

          {exposure && (
            <div className="flex flex-col gap-1 font-mono text-xs">
              <span className="text-micro text-ink-dim uppercase">Personnel exposure</span>
              <div
                className={clsx(
                  'border rounded px-2.5 py-1 bg-panel-2/50 flex flex-col gap-0.5',
                  exposure.headcountAtRisk > 0 ? 'border-near/40 text-near' : 'border-line text-ink-dim'
                )}
              >
                <span className="font-bold tabular-nums">
                  {exposure.headcountAtRisk} AT RISK
                </span>
                <span className="text-micro text-ink-dim">
                  {exposure.inZone.length} in zone · {exposure.inAdjacent.length} adjacent
                  {exposure.staleFixes > 0 && ` · ${exposure.staleFixes} stale fix`}
                </span>
              </div>
            </div>
          )}

          {finding.owner && (
            <div className="flex flex-col gap-1 font-mono text-xs">
              <span className="text-micro text-ink-dim uppercase">Assignee</span>
              <div className="border border-line rounded px-2.5 py-1 bg-panel-2/50 text-ink uppercase">
                {finding.owner}
              </div>
            </div>
          )}

          <div className="mt-auto flex flex-col gap-2 pt-4 border-t border-line">
            {finding.shadow && (
              <Button
                variant="primary"
                size="sm"
                onClick={async () => {
                  try {
                    // Update state to live (shadow = false) and notify
                    await transitionFinding(
                      finding.findingId,
                      'acknowledged',
                      'Promoted shadow finding to live alert',
                      'shadow-promote',
                    );
                    onSuccess();
                    onClose();
                  } catch (err) {
                    console.error('[DetailModal] Promotion failed:', err);
                  }
                }}
                className="w-full text-micro font-mono font-bold uppercase bg-near/20 border-near/40 text-near hover:bg-near/30"
              >
                Promote to Live
              </Button>
            )}
            <ExportEvidenceButton finding={finding} />
            <ExportIncidentReportButton finding={finding} />
          </div>
        </div>

        {/* Right column: Dynamic Tabs Area */}
        <div className="flex-1 flex flex-col gap-3 overflow-hidden">
          {/* Tab Navigation header */}
          <div className="flex border-b border-line pb-0.5 select-none shrink-0">
            {tabs.map((tab) => (
              <button
                key={tab.value}
                onClick={() => setActiveTab(tab.value)}
                className={clsx(
                  'flex items-center gap-1.5 h-8 px-3 text-xs font-semibold font-mono border-b-2 transition-all cursor-pointer',
                  activeTab === tab.value
                    ? 'border-accent text-accent'
                    : 'border-transparent text-ink-dim hover:text-ink hover:border-line'
                )}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab Contents Viewport */}
          <div className="flex-1 overflow-y-auto pr-1">
            {activeTab === 'overview' && (
              <div className="flex flex-col gap-4">
                <div className="flex flex-col gap-1.5">
                  <h3 className="text-base font-bold text-ink">{finding.title}</h3>
                  <p className="text-xs text-ink-dim/90 leading-relaxed">
                    A compound safety risk finding was triggered when several independent signals converged. 
                    The predictive engine estimates a breach window classification of <span className="font-semibold text-accent">{finding.leadTimeBand}</span>.
                  </p>
                </div>

                {finding.counterfactual && (
                  <div className="bg-panel-2/30 border border-line p-3 rounded flex flex-col gap-1">
                    <span className="text-micro font-mono font-bold text-accent uppercase">Alternative Course (Counterfactual)</span>
                    <p className="text-xs italic text-ink-dim leading-relaxed">↳ {finding.counterfactual}</p>
                  </div>
                )}

                {finding.confidenceDegraded && (
                  <div className="bg-imminent/5 border border-imminent/10 p-3 rounded flex items-start gap-2 text-xs text-imminent leading-normal">
                    <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold">Urgency Quality Degraded:</span> The predictive confidence score has been degraded due to stale or unreliable signals:
                      <span className="font-semibold block mt-1 font-mono">{finding.confidenceDegradedBy.join(', ')}</span>
                    </div>
                  </div>
                )}

                <InvestigationPanel findingId={finding.findingId} />
              </div>
            )}

            {activeTab === 'chart' && (
              <div className="h-full flex items-center justify-center">
                <TemporalConvergenceChart finding={finding} />
              </div>
            )}

            {activeTab === 'lineage' && (
              <div className="flex flex-col gap-3 font-mono text-xs">
                {finding.lineage && finding.lineage.length > 0 ? (
                  finding.lineage.map((item, idx) => {
                    const signal = finding.contributingSignals?.find((s) => `${s.kind}:${s.refId}` === item);
                    return (
                      <div key={idx} className="p-3 border border-line bg-panel-2/30 rounded flex flex-col gap-1">
                        <div className="flex justify-between items-center text-ink-dim">
                          <span className="font-bold text-ink uppercase">{item}</span>
                          {signal?.ts && (
                            <span className="text-micro">{new Date(signal.ts).toLocaleTimeString()}</span>
                          )}
                        </div>
                        {signal?.summary && (
                          <span className="text-micro text-ink-dim leading-normal">{signal.summary}</span>
                        )}
                      </div>
                    );
                  })
                ) : (
                  <div className="text-ink-dim italic">No evidence signals attached.</div>
                )}
              </div>
            )}

            {activeTab === 'audit' && <FindingAuditTab findingId={finding.findingId} />}
          </div>
        </div>
      </div>
    </Modal>
  );
}
