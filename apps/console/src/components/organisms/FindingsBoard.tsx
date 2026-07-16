import { useEffect, useState } from 'react';
import type { RiskFinding, FindingState, FeedbackVerdict } from '@/types';
import { FindingCard } from '@/components/organisms/FindingCard';
import { SnoozeDialog } from '@/components/molecules/SnoozeDialog';
import { AssignDialog } from '@/components/molecules/AssignDialog';
import { FeedbackModal } from '@/components/molecules/FeedbackModal';
import { FindingDetailModal } from '@/components/organisms/FindingDetailModal';
import { EmptyState } from '@/components/atoms';
import { useFindingsStore } from '@/stores/findings';
import { Inbox } from 'lucide-react';
import clsx from 'clsx';

const COLUMNS: { state: FindingState; label: string; headerColor: string }[] = [
  { state: 'new', label: 'New', headerColor: 'border-t-2 border-t-imminent' },
  { state: 'acknowledged', label: 'Acknowledged', headerColor: 'border-t-2 border-t-near' },
  { state: 'assigned', label: 'Assigned', headerColor: 'border-t-2 border-t-watch' },
  { state: 'in-progress', label: 'In progress', headerColor: 'border-t-2 border-t-accent' },
  { state: 'escalated', label: 'Escalated', headerColor: 'border-t-2 border-t-imminent' },
  { state: 'resolved', label: 'Resolved', headerColor: 'border-t-2 border-t-ok' },
];

interface FindingsBoardProps {
  findings: RiskFinding[];
  onChange: () => void;
}

export function FindingsBoard({ findings, onChange }: FindingsBoardProps) {
  const [snoozeFinding, setSnoozeFinding] = useState<RiskFinding | null>(null);
  const [assignFinding, setAssignFinding] = useState<RiskFinding | null>(null);
  const [feedbackFinding, setFeedbackFinding] = useState<RiskFinding | null>(null);
  const [feedbackVerdict, setFeedbackVerdict] = useState<FeedbackVerdict | null>(null);
  const [detailFinding, setDetailFinding] = useState<RiskFinding | null>(null);
  const { selectedId, setSelectedId } = useFindingsStore();

  // The command palette selects a finding by id; open its detail modal here.
  useEffect(() => {
    if (!selectedId) return;
    const hit = findings.find((f) => f.findingId === selectedId);
    if (hit) setDetailFinding(hit);
    setSelectedId(null);
  }, [selectedId, findings, setSelectedId]);

  const handleOpenFeedback = (finding: RiskFinding, verdict: FeedbackVerdict) => {
    setFeedbackFinding(finding);
    setFeedbackVerdict(verdict);
  };

  return (
    <div className="h-full w-full overflow-x-auto overflow-y-hidden pb-2 scrollbar">
      <div className="flex gap-3 h-full min-w-[1200px] px-1 select-none">
        {COLUMNS.map(({ state, label, headerColor }) => {
          const items = findings.filter((f) => f.state === state);

          return (
            <section
              key={state}
              className={clsx(
                'flex-1 flex flex-col h-full bg-panel/30 border border-line rounded-md overflow-hidden',
                headerColor
              )}
            >
              {/* Column Header */}
              <div className="h-9 px-3 border-b border-line flex items-center justify-between shrink-0 select-none">
                <span className="text-micro font-mono font-medium text-ink-dim uppercase tracking-[0.1em]">
                  {label}
                </span>
                <span
                  className={clsx(
                    'min-w-[20px] h-[18px] px-1 inline-flex items-center justify-center rounded-sm border text-micro font-mono tabular-nums',
                    items.length > 0
                      ? 'border-line text-ink bg-panel-2'
                      : 'border-transparent text-ink-dim/40'
                  )}
                >
                  {items.length}
                </span>
              </div>

              {/* Column Cards Container */}
              <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-2 scrollbar select-text">
                {items.length === 0 ? (
                  <EmptyState
                    icon={<Inbox />}
                    title="Nothing here"
                    className="flex-1 border-line/50"
                  />
                ) : (
                  items.map((f) => (
                    <FindingCard
                      key={f.findingId}
                      finding={f}
                      onChange={onChange}
                      onOpenSnooze={setSnoozeFinding}
                      onOpenAssign={setAssignFinding}
                      onOpenFeedback={handleOpenFeedback}
                      onOpenDetail={setDetailFinding}
                    />
                  ))
                )}
              </div>
            </section>
          );
        })}
      </div>

      {/* Snooze dialog popup */}
      <SnoozeDialog
        finding={snoozeFinding}
        isOpen={snoozeFinding !== null}
        onClose={() => setSnoozeFinding(null)}
        onSuccess={onChange}
      />

      {/* Assign dialog popup */}
      <AssignDialog
        finding={assignFinding}
        isOpen={assignFinding !== null}
        onClose={() => setAssignFinding(null)}
        onSuccess={onChange}
      />

      {/* Feedback dialog popup */}
      <FeedbackModal
        finding={feedbackFinding}
        verdict={feedbackVerdict}
        isOpen={feedbackFinding !== null && feedbackVerdict !== null}
        onClose={() => {
          setFeedbackFinding(null);
          setFeedbackVerdict(null);
        }}
        onSuccess={onChange}
      />

      {/* Details dialog popup */}
      <FindingDetailModal
        finding={detailFinding}
        isOpen={detailFinding !== null}
        onClose={() => setDetailFinding(null)}
        onSuccess={onChange}
      />
    </div>
  );
}
