import { AlertFatigueMetrics } from '@/components/organisms/AlertFatigueMetrics';
import { ThresholdConfig } from '@/components/organisms/ThresholdConfig';
import { RulesEditor } from '@/components/organisms/RulesEditor';

export default function AdminView() {
  return (
    <div className="flex flex-col gap-6 p-4 h-[calc(100vh-80px)] overflow-y-auto scrollbar select-text text-ink">
      {/* Header section */}
      <div className="flex flex-col gap-1 border-b border-line pb-3 select-none">
        <h1 className="text-lg font-bold uppercase font-mono tracking-wide">
          Alert Fatigue Management & Configuration
        </h1>
        <p className="text-xs text-ink-dim font-mono">
          Monitor shift limits, false alarm ratios, and zone-based warning thresholds.
        </p>
      </div>

      {/* Main KPI and Recharts Dashboard */}
      <AlertFatigueMetrics />

      {/* Configuration Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ThresholdConfig />
        <RulesEditor />
      </div>
    </div>
  );
}
