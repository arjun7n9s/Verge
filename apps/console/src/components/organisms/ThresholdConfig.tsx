import { useState } from 'react';
import { Card, Button } from '@/components/atoms';
import { Settings, Save, AlertCircle, CheckCircle } from 'lucide-react';

interface ZoneThreshold {
  zoneId: string;
  sensorType: string;
  low: number;
  high: number;
  critical: number;
  unit: string;
}

const INITIAL_THRESHOLDS: ZoneThreshold[] = [
  { zoneId: 'Zone 4', sensorType: 'Methane (CH4)', low: 0.2, high: 0.5, critical: 1.0, unit: '% LEL' },
  { zoneId: 'Zone 12', sensorType: 'Temperature', low: 60, high: 75, critical: 80, unit: '°C' },
  { zoneId: 'Zone 2', sensorType: 'Nitrogen Purge', low: 0.8, high: 1.2, critical: 1.5, unit: 'bar' },
  { zoneId: 'Zone 8', sensorType: 'Sulfur (H2S)', low: 5, high: 10, critical: 15, unit: 'ppm' },
];

export function ThresholdConfig() {
  const [thresholds, setThresholds] = useState<ZoneThreshold[]>(INITIAL_THRESHOLDS);
  const [editIndex, setEditIndex] = useState<number | null>(null);
  const [editValues, setEditValues] = useState<ZoneThreshold | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const startEdit = (idx: number) => {
    setEditIndex(idx);
    setEditValues({ ...thresholds[idx] });
  };

  const handleValueChange = (field: 'low' | 'high' | 'critical', val: string) => {
    if (!editValues) return;
    const num = parseFloat(val);
    setEditValues({
      ...editValues,
      [field]: isNaN(num) ? 0 : num,
    });
  };

  const saveEdit = () => {
    if (!editValues || editIndex === null) return;
    
    // Validate order: low < high < critical
    if (editValues.low >= editValues.high || editValues.high >= editValues.critical) {
      setMessage({ text: 'Validation Error: Thresholds must satisfy Low < High < Critical.', type: 'error' });
      return;
    }

    const updated = [...thresholds];
    updated[editIndex] = editValues;
    setThresholds(updated);
    setEditIndex(null);
    setEditValues(null);
    setMessage({ text: 'Threshold configurations updated successfully.', type: 'success' });

    setTimeout(() => setMessage(null), 3000);
  };

  return (
    <Card className="p-3 bg-panel border-line text-ink font-mono text-xs select-none">
      <div className="flex justify-between items-center border-b border-line pb-2.5 mb-3">
        <span className="font-bold text-ink-dim uppercase flex items-center gap-1.5">
          <Settings className="h-4 w-4" />
          Sensor Alarm Threshold Matrix
        </span>
      </div>

      {message && (
        <div className={`p-2.5 rounded border text-micro mb-3 flex items-center gap-2 select-text ${
          message.type === 'error' ? 'bg-imminent/10 border-imminent/20 text-imminent' : 'bg-ok/10 border-ok/20 text-ok'
        }`}>
          {message.type === 'error' ? <AlertCircle className="h-4 w-4" /> : <CheckCircle className="h-4 w-4" />}
          <span>{message.text}</span>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-left font-mono text-micro select-text">
          <thead className="bg-panel-2 border-b border-line text-ink-dim uppercase select-none">
            <tr>
              <th className="p-2">Zone</th>
              <th className="p-2">Sensor Class</th>
              <th className="p-2 w-20 text-center">Low</th>
              <th className="p-2 w-20 text-center">High</th>
              <th className="p-2 w-20 text-center">Critical</th>
              <th className="p-2 w-16 text-center select-none">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line/30">
            {thresholds.map((t, idx) => {
              const isEditing = editIndex === idx;
              return (
                <tr key={idx} className="hover:bg-panel-2/10">
                  <td className="p-2 font-bold text-ink">{t.zoneId}</td>
                  <td className="p-2 text-ink-dim">{t.sensorType}</td>
                  <td className="p-2 text-center tabular-nums">
                    {isEditing ? (
                      <input
                        type="number"
                        step="any"
                        value={editValues?.low ?? 0}
                        onChange={(e) => handleValueChange('low', e.target.value)}
                        className="w-16 h-6 bg-bg border border-line rounded px-1 text-center font-mono text-micro focus:outline-none focus:border-accent"
                      />
                    ) : (
                      `${t.low} ${t.unit}`
                    )}
                  </td>
                  <td className="p-2 text-center tabular-nums">
                    {isEditing ? (
                      <input
                        type="number"
                        step="any"
                        value={editValues?.high ?? 0}
                        onChange={(e) => handleValueChange('high', e.target.value)}
                        className="w-16 h-6 bg-bg border border-line rounded px-1 text-center font-mono text-micro focus:outline-none focus:border-accent"
                      />
                    ) : (
                      `${t.high} ${t.unit}`
                    )}
                  </td>
                  <td className="p-2 text-center tabular-nums">
                    {isEditing ? (
                      <input
                        type="number"
                        step="any"
                        value={editValues?.critical ?? 0}
                        onChange={(e) => handleValueChange('critical', e.target.value)}
                        className="w-16 h-6 bg-bg border border-line rounded px-1 text-center font-mono text-micro focus:outline-none focus:border-accent"
                      />
                    ) : (
                      `${t.critical} ${t.unit}`
                    )}
                  </td>
                  <td className="p-2 text-center select-none">
                    {isEditing ? (
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={saveEdit}
                        icon={<Save className="h-3 w-3" />}
                        className="h-6 w-14 text-micro py-0"
                      >
                        Save
                      </Button>
                    ) : (
                      <button
                        onClick={() => startEdit(idx)}
                        className="text-accent hover:underline text-micro cursor-pointer font-bold uppercase"
                      >
                        Edit
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
