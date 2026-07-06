import { useState } from 'react';
import { Card, Badge, Button } from '@/components/atoms';
import { ArrowRightLeft, FileText, ClipboardList, CheckCircle2 } from 'lucide-react';
import { transitionFinding } from '@/api';

interface HandoverTask {
  id: string;
  title: string;
  zone: string;
  state: string;
}

const MOCK_TASKS: HandoverTask[] = [
  { id: 'rf-0491', title: 'Hydrocarbon Gas Accumulation', zone: 'Zone 4 (Primary Reformer)', state: 'new' },
  { id: 'rf-1204', title: 'Compressor Bearing Thermal Runaway', zone: 'Zone 12 (Confined Compressor)', state: 'acknowledged' },
];

export default function ShiftHandoverView() {
  const [logText, setLogText] = useState('');
  const [signedOff, setSignedOff] = useState(false);
  const [tasks] = useState<HandoverTask[]>(MOCK_TASKS);

  const handleSignOff = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!logText.trim()) return;

    try {
      // Simulate audit logs transition for handover
      for (const task of tasks) {
        await transitionFinding(task.id, 'assigned', `Shift Handover: ${logText.trim()}`);
      }
      setSignedOff(true);
    } catch (err) {
      console.error('[HandoverSignoff] Failed:', err);
    }
  };

  return (
    <div className="flex flex-col gap-6 p-4 h-[calc(100vh-80px)] overflow-y-auto scrollbar select-text text-ink font-sans">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-line pb-3 select-none shrink-0">
        <div className="flex flex-col gap-1">
          <h1 className="text-lg font-bold uppercase font-mono tracking-wide flex items-center gap-2">
            <ArrowRightLeft className="h-5 w-5 text-accent" />
            Shift Handover Console
          </h1>
          <p className="text-xs text-ink-dim font-mono">
            Review active alarms, outline unresolved tasks, and sign off the shift transfer log.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Left: Active tasks to hand over */}
        <div className="flex flex-col gap-3">
          <span className="text-xs font-mono font-bold text-ink-dim uppercase select-none flex items-center gap-1.5">
            <ClipboardList className="h-4 w-4" />
            Outstanding Shift Alarms ({tasks.length})
          </span>

          <div className="flex flex-col gap-2.5">
            {tasks.map((task) => (
              <Card key={task.id} className="p-3 border border-line bg-panel-2/30 flex justify-between items-center">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <Badge variant="generic" color="near" className="font-mono text-micro font-bold py-0.5">
                      {task.id}
                    </Badge>
                    <span className="text-xs font-bold text-ink">{task.title}</span>
                  </div>
                  <span className="text-micro font-mono text-ink-dim uppercase">{task.zone}</span>
                </div>
                <Badge variant="generic" color="near" className="uppercase text-micro scale-90">
                  {task.state}
                </Badge>
              </Card>
            ))}
          </div>
        </div>

        {/* Right: Handover notes and sign-off */}
        <div className="flex flex-col gap-3">
          <span className="text-xs font-mono font-bold text-ink-dim uppercase select-none flex items-center gap-1.5">
            <FileText className="h-4 w-4" />
            Shift Transfer Log
          </span>

          {signedOff ? (
            <Card className="p-4 border border-ok/30 bg-ok/5 flex flex-col items-center gap-3 text-center">
              <CheckCircle2 className="h-10 w-10 text-ok animate-bounce" />
              <h3 className="text-xs font-bold font-mono text-ok uppercase">
                Shift handover signed off successfully
              </h3>
              <p className="text-xs text-ink-dim font-mono leading-relaxed max-w-xs">
                Handover details have been submitted to the blockchain audit log. The next shift has assumed responsibility.
              </p>
            </Card>
          ) : (
            <form onSubmit={handleSignOff} className="flex flex-col gap-3">
              <textarea
                placeholder="Write handover log summary (e.g. status of reformer seals, permit renewals)..."
                value={logText}
                onChange={(e) => setLogText(e.target.value)}
                className="h-28 p-2.5 rounded border border-line text-xs bg-panel text-ink placeholder:text-ink-dim/40 focus:outline-none select-text leading-relaxed"
                required
              />

              <Button
                variant="primary"
                size="sm"
                type="submit"
                disabled={!logText.trim()}
                className="uppercase text-micro font-bold h-8 tracking-wider w-36 self-end"
              >
                Sign Off Shift
              </Button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
