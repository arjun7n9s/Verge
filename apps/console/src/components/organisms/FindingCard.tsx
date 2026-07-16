import { useState } from 'react';
import type { RiskFinding, FeedbackVerdict } from '@/types';
import { transitionFinding } from '@/api';
import { Badge, Button, Card } from '@/components/atoms';
import { LeadTimeGauge } from '@/components/molecules/LeadTimeGauge';
import { toast } from '@/stores/toasts';
import {
  AlertTriangle,
  User,
  Clock,
  ThumbsUp,
  ThumbsDown,
  ChevronRight,
  Cpu,
  FileText,
  Wrench,
  Camera,
  Activity,
} from 'lucide-react';
import clsx from 'clsx';

interface FindingCardProps {
  finding: RiskFinding;
  onChange: () => void;
  onOpenSnooze?: (finding: RiskFinding) => void;
  onOpenAssign?: (finding: RiskFinding) => void;
  onOpenFeedback?: (finding: RiskFinding, verdict: FeedbackVerdict) => void;
  onOpenDetail?: (finding: RiskFinding) => void;
}

// Function to map a lineage label to an icon
function getLineageIcon(label: string) {
  const lowercase = label.toLowerCase();
  if (lowercase.includes('sensor') || lowercase.includes('reading') || lowercase.includes('temp') || lowercase.includes('gas') || lowercase.includes('pres')) {
    return <Cpu className="h-3 w-3 shrink-0 text-accent" />;
  }
  if (lowercase.includes('permit') || lowercase.includes('ptw')) {
    return <FileText className="h-3 w-3 shrink-0 text-watch" />;
  }
  if (lowercase.includes('maintenance') || lowercase.includes('maint') || lowercase.includes('work')) {
    return <Wrench className="h-3 w-3 shrink-0 text-near" />;
  }
  if (lowercase.includes('cctv') || lowercase.includes('camera') || lowercase.includes('frame')) {
    return <Camera className="h-3 w-3 shrink-0 text-ok" />;
  }
  return <Activity className="h-3 w-3 shrink-0 text-ink-dim" />;
}

export function FindingCard({
  finding,
  onChange,
  onOpenSnooze,
  onOpenAssign,
  onOpenFeedback,
  onOpenDetail,
}: FindingCardProps) {
  const [isTransitioning, setIsTransitioning] = useState(false);

  const ack = async () => {
    setIsTransitioning(true);
    try {
      await transitionFinding(finding.findingId, 'acknowledged', 'Acknowledged by operator');
      toast.ok(`${finding.findingId} acknowledged`);
      onChange();
    } catch (err) {
      console.error('[FindingCard] Ack failure:', err);
      toast.error(`Failed to acknowledge ${finding.findingId}`);
    } finally {
      setIsTransitioning(false);
    }
  };

  return (
    <Card
      role="article"
      aria-labelledby={`finding-${finding.findingId}-title`}
      className={clsx(
        'group flex flex-col gap-3 relative overflow-hidden transition-all duration-fast select-text',
        // Highlights card outline when imminent risk and not closed
        finding.leadTimeBand === 'IMMINENT' && finding.state !== 'closed' && 'border-imminent/40 hover:border-imminent/70'
      )}
    >
      {/* Risk Ribbon Indicator (Left edge accent for Imminent/Near) */}
      <div
        className={clsx(
          'absolute left-0 top-0 bottom-0 w-[3px]',
          finding.leadTimeBand === 'IMMINENT' ? 'bg-imminent' :
          finding.leadTimeBand === 'NEAR' ? 'bg-near' :
          finding.leadTimeBand === 'WATCH' ? 'bg-watch' : 'bg-unknown'
        )}
      />

      {/* Card Header metadata */}
      <header className="flex items-center justify-between gap-2 text-micro font-mono select-none">
        <div className="flex items-center gap-1.5">
          <span className="text-ink-dim font-medium tracking-[0.06em]">{finding.zoneId}</span>
          {finding.shadow && (
            <Badge variant="generic" color="near" className="text-micro font-bold border-dashed">
              SHADOW
            </Badge>
          )}
        </div>
        <span className="tabular-nums text-ink-dim/70" title="Detection confidence">
          {(finding.confidence * 100).toFixed(0)}%
        </span>
      </header>

      {/* Signature lead-time tape (replaces the band badge) */}
      <LeadTimeGauge band={finding.leadTimeBand} basis={finding.leadTimeBasis} size="sm" />

      {/* Card Title */}
      <div>
        <h3
          id={`finding-${finding.findingId}-title`}
          onClick={() => onOpenDetail?.(finding)}
          className="text-sm font-semibold text-ink leading-snug hover:text-accent flex items-start gap-1 cursor-pointer"
        >
          {finding.title}
          <ChevronRight className="h-4 w-4 shrink-0 text-ink-dim/40 self-center" />
        </h3>
      </div>

      {/* Degradation / Counterfactual status banners */}
      {finding.confidenceDegraded && (
        <div className="flex items-start gap-1.5 bg-imminent/5 border border-imminent/10 p-1.5 rounded text-micro text-imminent leading-normal">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0 self-start" />
          <div>
            <span>ESTIMATE DEGRADED &mdash; SUSPECT SIGNAL INPUTS:</span>
            <span className="font-semibold ml-1">{finding.confidenceDegradedBy.join(', ')}</span>
          </div>
        </div>
      )}

      {finding.counterfactual && (
        <p className="text-xs text-ink-dim/70 font-mono italic leading-normal border-l border-line pl-2 ml-1">
          ↳ {finding.counterfactual}
        </p>
      )}

      {/* Source Lineage Chips */}
      {finding.lineage && finding.lineage.length > 0 && (
        <div className="flex flex-wrap gap-1.5 select-none" aria-label="Contributing evidence signals">
          {finding.lineage.map((item) => (
            <div
              key={item}
              className="inline-flex items-center gap-1 bg-panel-2 border border-line px-1.5 py-0.5 rounded-sm text-micro text-ink-dim font-mono hover:text-ink cursor-pointer transition-colors"
            >
              {getLineageIcon(item)}
              {item}
            </div>
          ))}
        </div>
      )}

      {/* Divider */}
      <div className="h-[1px] bg-line w-full select-none" />

      {/* Footer Operator Actions */}
      <footer className="flex items-center justify-between select-none">
        <div className="flex items-center gap-1.5">
          {finding.state === 'new' ? (
            <Button
              variant="primary"
              size="sm"
              loading={isTransitioning}
              onClick={ack}
              className="text-micro font-bold uppercase"
              aria-label="Acknowledge finding"
            >
              Acknowledge
            </Button>
          ) : (
            <div className="text-micro font-mono text-ink-dim flex items-center gap-1 bg-panel-2 px-2 py-0.5 border border-line rounded">
              <span className="h-1.5 w-1.5 rounded-full bg-accent" />
              <span className="uppercase">{finding.state}</span>
            </div>
          )}

          {/* Quick Assign / Snooze (Only if not closed or resolved) */}
          {finding.state !== 'closed' && finding.state !== 'resolved' && (
            <>
              {onOpenAssign && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onOpenAssign(finding)}
                  className="p-1 h-6 hover:bg-panel-2 text-ink-dim"
                  aria-label="Assign finding"
                  title="Assign to owner"
                >
                  <User className="h-3.5 w-3.5" />
                </Button>
              )}
              {onOpenSnooze && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onOpenSnooze(finding)}
                  className="p-1 h-6 hover:bg-panel-2 text-ink-dim"
                  aria-label="Snooze finding"
                  title="Snooze alert"
                >
                  <Clock className="h-3.5 w-3.5" />
                </Button>
              )}
            </>
          )}
        </div>

        {/* Feedback thumbs — recede until the card is hovered */}
        <div className="flex items-center gap-1 opacity-50 group-hover:opacity-100 transition-opacity duration-fast">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onOpenFeedback?.(finding, 'useful')}
            className="p-1 h-6 hover:text-ok text-ink-dim hover:bg-panel-2"
            aria-label="Mark finding as useful"
            title="Mark useful"
          >
            <ThumbsUp className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onOpenFeedback?.(finding, 'false-alarm')}
            className="p-1 h-6 hover:text-imminent text-ink-dim hover:bg-panel-2"
            aria-label="Mark finding as false alarm"
            title="Mark false alarm"
          >
            <ThumbsDown className="h-3.5 w-3.5" />
          </Button>
        </div>
      </footer>
    </Card>
  );
}
