import { useState } from 'react';
import type { RiskFinding, FeedbackVerdict } from '@/types';
import { submitFeedback } from '@/api';
import { Modal, Button } from '@/components/atoms';

interface FeedbackModalProps {
  finding: RiskFinding | null;
  verdict: FeedbackVerdict | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const REASON_CODES = [
  { value: 'noise', label: 'Signal Noise' },
  { value: 'stale-data', label: 'Stale Sensor Data' },
  { value: 'already-known', label: 'Already Known/Active Incident' },
  { value: 'not-actionable', label: 'Not Actionable Alert' },
  { value: 'duplicate', label: 'Duplicate Finding' },
  { value: 'wrong-zone', label: 'Incorrect Zone Mapping' },
  { value: 'other', label: 'Other Justification' },
];

import DOMPurify from 'dompurify';

export function FeedbackModal({ finding, verdict, isOpen, onClose, onSuccess }: FeedbackModalProps) {
  const [reasonCode, setReasonCode] = useState<string>('noise');
  const [reasonText, setReasonText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!finding || !verdict) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const sanitizedText = DOMPurify.sanitize(reasonText.trim());
      await submitFeedback(
        finding.findingId,
        verdict,
        reasonCode,
        sanitizedText || undefined
      );
      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Feedback submission failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const footer = (
    <>
      <Button variant="ghost" onClick={onClose} disabled={isSubmitting}>
        Cancel
      </Button>
      <Button
        variant={verdict === 'false-alarm' ? 'danger' : 'primary'}
        onClick={handleSubmit}
        loading={isSubmitting}
      >
        Submit Feedback
      </Button>
    </>
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Submit Operator Feedback"
      description={`Record accuracy feedback for ${finding.zoneId}: ${finding.title}`}
      footer={footer}
      size="md"
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4 text-ink">
        {error && (
          <div className="text-xs text-imminent bg-imminent/10 border border-imminent/20 p-2 rounded">
            {error}
          </div>
        )}

        {/* Verdict Display */}
        <div className="flex items-center gap-2 select-none">
          <span className="text-xs font-medium text-ink-dim uppercase">VERDICT:</span>
          <span
            className={`text-xs font-mono font-bold px-2 py-0.5 rounded border uppercase ${
              verdict === 'useful'
                ? 'bg-ok/10 border-ok/30 text-ok'
                : verdict === 'not-useful'
                ? 'bg-unknown/10 border-unknown/30 text-unknown'
                : 'bg-imminent/10 border-imminent/30 text-imminent'
            }`}
          >
            {verdict.replace('-', ' ')}
          </span>
        </div>

        {/* Reason Code Dropdown */}
        <div className="flex flex-col gap-1.5 select-none">
          <label htmlFor="reason-code-select" className="text-xs font-medium text-ink-dim">
            Reason Code Justification
          </label>
          <select
            id="reason-code-select"
            value={reasonCode}
            onChange={(e) => setReasonCode(e.target.value)}
            className="h-8 px-2.5 rounded border border-line text-sm bg-panel-2 text-ink focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent"
          >
            {REASON_CODES.map((code) => (
              <option key={code.value} value={code.value} className="bg-panel">
                {code.label}
              </option>
            ))}
          </select>
        </div>

        {/* Custom text comments */}
        <div className="flex flex-col gap-1.5">
          <label htmlFor="reason-comments" className="text-xs font-medium text-ink-dim">
            Memos & Comments (Optional)
          </label>
          <textarea
            id="reason-comments"
            rows={3}
            placeholder="Provide additional technical observations or incident logs..."
            value={reasonText}
            onChange={(e) => setReasonText(e.target.value)}
            className="p-2 border border-line rounded text-sm bg-panel-2 text-ink placeholder:text-ink-dim/40 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent resize-none"
          />
        </div>
      </form>
    </Modal>
  );
}
