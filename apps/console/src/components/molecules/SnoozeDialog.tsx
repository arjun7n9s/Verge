import { useState } from 'react';
import type { RiskFinding } from '@/types';
import { transitionFinding } from '@/api';
import { Modal, Button, Input } from '@/components/atoms';

interface SnoozeDialogProps {
  finding: RiskFinding | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const PRESET_DURATIONS = [
  { label: '15 Min', value: 15 },
  { label: '30 Min', value: 30 },
  { label: '1 Hour', value: 60 },
  { label: '2 Hours', value: 120 },
  { label: '4 Hours', value: 240 },
  { label: '12 Hours', value: 720 },
];

export function SnoozeDialog({ finding, isOpen, onClose, onSuccess }: SnoozeDialogProps) {
  const [duration, setDuration] = useState<number>(30); // Default 30 min
  const [reason, setReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!finding) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      setError('A snooze reason is mandatory for safety compliance auditing.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await transitionFinding(
        finding.findingId,
        'snoozed',
        `Snoozed for ${duration} min. Reason: ${reason.trim()}`,
        'operator-defer',
      );
      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Snooze transition failed');
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
        variant="primary"
        onClick={handleSubmit}
        loading={isSubmitting}
        disabled={!reason.trim()}
      >
        Confirm Snooze
      </Button>
    </>
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Snooze Finding Alert"
      description={`Temporarily silence alerts for ${finding.zoneId}: ${finding.title}`}
      footer={footer}
      size="md"
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {/* Preset selector */}
        <div className="flex flex-col gap-1.5">
          <span className="text-xs font-medium text-ink-dim select-none">Select Duration</span>
          <div className="grid grid-cols-3 gap-2">
            {PRESET_DURATIONS.map((preset) => (
              <button
                key={preset.value}
                type="button"
                onClick={() => setDuration(preset.value)}
                className={`h-8 rounded border text-xs font-semibold font-mono transition-all cursor-pointer ${
                  duration === preset.value
                    ? 'bg-accent/10 border-accent text-accent'
                    : 'bg-panel-2 border-line text-ink-dim hover:text-ink hover:border-line/75'
                }`}
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>

        {/* Reason Input */}
        <div className="flex flex-col gap-1.5">
          <Input
            label="Snooze Justification (Mandatory)"
            placeholder="e.g. Maya dispatching Field Tech to inspect gas line"
            value={reason}
            onChange={(e) => {
              setReason(e.target.value);
              if (error) setError(null);
            }}
            error={error ?? undefined}
            required
            autoFocus
          />
        </div>
      </form>
    </Modal>
  );
}
