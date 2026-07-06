import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Badge, Button } from '@/components/atoms';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { AlertTriangle, Send, CheckCircle, AlertCircle } from 'lucide-react';
import { getFleetSummary, type FleetPlant } from '@/api/fleet';

export default function FleetView() {
  const navigate = useNavigate();
  const [plants, setPlants] = useState<FleetPlant[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [bulletin, setBulletin] = useState('');
  const [bulletins, setBulletins] = useState<string[]>([
    'SAFETY CIRCULAR: Pre-shift safety walks mandated on all gas compressor seals fleet-wide.',
  ]);

  useEffect(() => {
    const load = async () => {
      try {
        const summary = await getFleetSummary();
        setPlants(summary.plants);
        setLoadError(null);
      } catch {
        setPlants([]);
        setLoadError('Fleet summary unavailable — start API with `make dev`.');
      }
    };
    void load();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, []);

  const handlePostBulletin = (e: React.FormEvent) => {
    e.preventDefault();
    if (!bulletin.trim()) return;
    setBulletins((prev) => [bulletin.trim(), ...prev]);
    setBulletin('');
  };

  const chartData = plants.map((p) => ({
    name: p.plantId.replace('PLT-', ''),
    TRIR: p.trir,
    'Sensor Health %': p.sensorHealth ?? 0,
    'Active Alarms': p.activeRisks,
  }));

  return (
    <div className="flex flex-col gap-6 p-4 h-[calc(100vh-80px)] overflow-y-auto scrollbar select-text text-ink">
      <div className="flex flex-col gap-1 border-b border-line pb-3 select-none">
        <h1 className="text-lg font-bold uppercase font-mono tracking-wide">
          Multi-Site Fleet Command Center
        </h1>
        <p className="text-xs text-ink-dim font-mono">
          Aggregate risk status, incident comparisons, and safety circulars across all production sites.
        </p>
      </div>

      {loadError && (
        <div className="bg-imminent/10 border border-imminent/20 text-imminent text-xs p-2 rounded flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {loadError}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="flex flex-col gap-3">
          <span className="text-xs font-mono font-bold text-ink-dim uppercase select-none">
            Active Production Facilities
          </span>
          {plants.length === 0 && !loadError && (
            <span className="text-xs font-mono text-ink-dim">Loading fleet…</span>
          )}
          {plants.map((plant) => (
            <Card
              key={plant.plantId}
              className={`p-3.5 border flex justify-between items-center ${
                plant.status === 'imminent'
                  ? 'border-imminent/30 bg-imminent/5'
                  : plant.status === 'near'
                  ? 'border-near/30 bg-near/5'
                  : 'border-line bg-panel-2/30'
              }`}
            >
              <div className="flex flex-col gap-1 pr-4">
                <div className="flex items-center gap-2">
                  <Badge
                    variant="generic"
                    color={plant.status === 'imminent' ? 'imminent' : plant.status === 'near' ? 'near' : 'ok'}
                    className="font-mono text-micro font-bold py-0.5"
                  >
                    {plant.plantId}
                  </Badge>
                  <span className="text-xs font-bold text-ink leading-relaxed">{plant.name}</span>
                </div>
                <span className="text-micro font-mono text-ink-dim uppercase">
                  Location: {plant.location}
                </span>
                <div className="flex items-center gap-3 text-micro font-mono text-ink-dim uppercase mt-1">
                  <span>
                    Alarms: <strong className="text-ink">{plant.activeRisks}</strong>
                    {plant.measured.activeRisks ? '' : ' (est.)'}
                  </span>
                  <span>
                    Sensor Health:{' '}
                    <strong className="text-ink">
                      {plant.sensorHealth != null ? `${plant.sensorHealth}%` : '—'}
                    </strong>
                  </span>
                  <span>
                    TRIR: <strong className="text-ink">{plant.trir}</strong>
                    {!plant.measured.trir && ' (baseline)'}
                  </span>
                </div>
              </div>

              <div className="flex flex-col gap-1.5 shrink-0 select-none">
                {plant.status === 'imminent' && (
                  <div className="flex items-center gap-1 text-micro font-mono text-imminent font-bold uppercase animate-pulse">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    IMMINENT HAZARDS
                  </div>
                )}
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    if (plant.plantId === 'PLT-VIZAG') navigate('/');
                  }}
                  disabled={plant.plantId !== 'PLT-VIZAG'}
                  className="text-micro font-mono font-bold uppercase text-ink-dim hover:text-ink"
                >
                  {plant.plantId === 'PLT-VIZAG' ? 'Drill Down' : 'Not Connected'}
                </Button>
              </div>
            </Card>
          ))}
        </div>

        <div className="flex flex-col gap-3">
          <span className="text-xs font-mono font-bold text-ink-dim uppercase select-none">
            Safety KPIs Comparison (TRIR / Alarms)
          </span>
          <div className="h-56 w-full border border-line bg-panel-2/30 p-3 rounded-md select-none font-mono text-micro">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                  <CartesianGrid stroke="#2a323d" strokeDasharray="3 3" />
                  <XAxis dataKey="name" stroke="#8b949e" tickLine={false} />
                  <YAxis stroke="#8b949e" tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#161b22',
                      borderColor: '#2a323d',
                      color: '#e6edf3',
                    }}
                  />
                  <Bar dataKey="TRIR" fill="#e8a33d" radius={[2, 2, 0, 0]} />
                  <Bar dataKey="Active Alarms" fill="#f06363" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <span className="text-ink-dim text-xs">No fleet data</span>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 border-t border-line pt-4">
        <div className="flex flex-col gap-3">
          <span className="text-xs font-mono font-bold text-ink-dim uppercase select-none">
            Safety Bulletins & Mutual Aid
          </span>
          <div className="flex flex-col gap-2.5">
            {bulletins.map((b, idx) => (
              <div
                key={idx}
                className="p-3 border border-line bg-panel-2/20 rounded flex items-start gap-2.5 text-xs text-ink-dim leading-relaxed font-mono"
              >
                <CheckCircle className="h-4 w-4 text-ok shrink-0 mt-0.5" />
                <span>{b}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-3">
          <span className="text-xs font-mono font-bold text-ink-dim uppercase select-none">
            Compose Broadcast Circular
          </span>
          <form onSubmit={handlePostBulletin} className="flex flex-col gap-3">
            <textarea
              placeholder="Write circular description here..."
              value={bulletin}
              onChange={(e) => setBulletin(e.target.value)}
              className="h-20 p-2.5 rounded border border-line text-xs bg-panel text-ink placeholder:text-ink-dim/40 focus:outline-none"
            />
            <Button
              variant="primary"
              size="sm"
              type="submit"
              disabled={!bulletin.trim()}
              icon={<Send className="h-3.5 w-3.5" />}
              className="uppercase text-micro font-bold h-8 tracking-wider w-36 self-end"
            >
              Broadcast
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
