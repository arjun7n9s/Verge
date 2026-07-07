import { useEffect, useMemo, useState } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { Card } from '@/components/atoms';
import { TrendingDown, ShieldAlert, Award } from 'lucide-react';
import { getFatigueMetrics, type FatigueMetrics } from '@/api/platform';

interface MetricCardProps {
  title: string;
  value: string | number;
  change: string;
  isPositive: boolean;
  icon: React.ReactNode;
}

function MetricCard({ title, value, change, isPositive, icon }: MetricCardProps) {
  return (
    <Card className="flex items-center justify-between p-4 bg-panel-2/30">
      <div className="flex flex-col gap-1">
        <span className="text-micro font-mono text-ink-dim uppercase">{title}</span>
        <span className="text-xl font-bold text-ink tabular-nums leading-none">{value}</span>
        <span
          className={`text-micro font-mono ${
            isPositive ? 'text-ok' : 'text-imminent'
          }`}
        >
          {change}
        </span>
      </div>
      <div className="p-2 bg-panel-2 rounded border border-line text-ink-dim shrink-0">
        {icon}
      </div>
    </Card>
  );
}

export function AlertFatigueMetrics() {
  const [metrics, setMetrics] = useState<FatigueMetrics | null>(null);

  useEffect(() => {
    getFatigueMetrics()
      .then(setMetrics)
      .catch(() => setMetrics(null));
  }, []);

  const chartData = useMemo(
    () => metrics?.trend ?? [],
    [metrics?.trend],
  );

  const zonesData = metrics?.zones ?? [];
  const fprPct = metrics?.falseAlarmRatio != null ? `${(metrics.falseAlarmRatio * 100).toFixed(1)}%` : '—';
  const actionPct =
    metrics?.operatorActionRate != null
      ? `${(metrics.operatorActionRate * 100).toFixed(1)}%`
      : '—';

  return (
    <div className="flex flex-col gap-4 text-ink select-none">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <MetricCard
          title="ALERTS PER SHIFT"
          value={metrics?.alertsPerShift ?? '—'}
          change={metrics?.measured ? 'FROM LIVE FINDINGS' : 'AWAITING FEEDBACK'}
          isPositive={true}
          icon={<ShieldAlert className="h-4 w-4" />}
        />
        <MetricCard
          title="FALSE ALARM RATIO"
          value={fprPct}
          change={metrics?.measured ? 'MEASURED FROM FEEDBACK' : 'RUN FEEDBACK TO MEASURE'}
          isPositive={metrics?.falseAlarmRatio != null && metrics.falseAlarmRatio < 0.2}
          icon={<TrendingDown className="h-4 w-4" />}
        />
        <MetricCard
          title="OPERATOR ACTION RATE"
          value={actionPct}
          change={metrics?.measured ? 'USEFUL / TOTAL FEEDBACK' : 'NOT YET MEASURED'}
          isPositive={true}
          icon={<Award className="h-4 w-4" />}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <Card className="lg:col-span-2 flex flex-col gap-3">
          <div className="flex items-center justify-between border-b border-line pb-2">
            <span className="text-xs font-mono font-bold text-ink uppercase tracking-wide">
              Signal-To-Noise Trend
            </span>
            <span className="text-micro font-mono text-ink-dim uppercase">
              {metrics?.measured ? 'LIVE FEEDBACK' : 'NO FEEDBACK YET'}
            </span>
          </div>

          <div className="h-48 w-full font-mono text-micro select-text">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                  <CartesianGrid stroke="#2a323d" strokeDasharray="3 3" />
                  <XAxis dataKey="date" stroke="#8b949e" tickLine={false} />
                  <YAxis stroke="#8b949e" tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#161b22',
                      borderColor: '#2a323d',
                      color: '#e6edf3',
                      borderRadius: '4px',
                    }}
                  />
                  <Line
                    name="False Alarms"
                    type="monotone"
                    dataKey="falseAlarms"
                    stroke="#f06363"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                  />
                  <Line
                    name="Useful Alerts"
                    type="monotone"
                    dataKey="useful"
                    stroke="#4ec98a"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-ink-dim text-xs font-mono">
                Submit finding feedback to populate the S/N chart.
              </div>
            )}
          </div>
        </Card>

        <Card className="flex flex-col gap-3">
          <div className="flex items-center justify-between border-b border-line pb-2">
            <span className="text-xs font-mono font-bold text-ink uppercase tracking-wide">
              Alert Volume vs Rate Limits
            </span>
            <span className="text-micro font-mono text-ink-dim uppercase">
              PER ZONE / 12H
            </span>
          </div>

          <div className="flex flex-col gap-3">
            {zonesData.length > 0 ? (
              zonesData.map((item) => (
                <div key={item.zoneId} className="flex flex-col gap-1 text-xs">
                  <div className="flex justify-between items-center text-ink-dim">
                    <span className="font-semibold text-ink font-mono">{item.zoneId}</span>
                    <span className="font-mono tabular-nums">
                      {item.current}/{item.limit} ({item.pct}%)
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-panel-2 rounded-full overflow-hidden border border-line">
                    <div
                      className={`h-full transition-all duration-slow ${
                        item.pct > 100 ? 'bg-imminent' : item.pct > 80 ? 'bg-near' : 'bg-ok'
                      }`}
                      style={{ width: `${Math.min(100, item.pct)}%` }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <div className="text-xs text-ink-dim font-mono">No recent zone alerts.</div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
