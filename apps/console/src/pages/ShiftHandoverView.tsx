import { useEffect, useRef, useState } from 'react';
import { Card, Badge, Button } from '@/components/atoms';
import { ArrowRightLeft, FileText, ClipboardList, CheckCircle2, Mic, Upload, AlertTriangle } from 'lucide-react';
import { getFindings, transitionFinding } from '@/api';
import { submitVoiceHandover, textToHandoverWav, type VoiceResult } from '@/api/voice';
import type { RiskFinding } from '@/types';

const OPEN_STATES = new Set(['new', 'acknowledged', 'assigned', 'in-progress', 'escalated', 'snoozed']);

export default function ShiftHandoverView() {
  const [findings, setFindings] = useState<RiskFinding[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [logText, setLogText] = useState('');
  const [signedOff, setSignedOff] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [voiceResult, setVoiceResult] = useState<VoiceResult | null>(null);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getFindings()
      .then((data) => {
        setFindings(data.filter((f) => !f.shadow && OPEN_STATES.has(f.state)));
        setLoadError(null);
      })
      .catch(() => {
        setFindings([]);
        setLoadError('Findings unavailable — start API with `make dev`.');
      });
  }, [signedOff]);

  const handleVoiceUpload = async (file: File) => {
    setAudioFile(file);
    setSubmitting(true);
    setVoiceResult(null);
    try {
      const result = await submitVoiceHandover(file, 'maya');
      setVoiceResult(result);
      if (result.transcript) {
        setLogText((prev) => (prev ? `${prev}\n\n${result.transcript}` : result.transcript));
      }
    } catch (err) {
      console.error('[HandoverVoice]', err);
      setVoiceResult({
        transcript: '',
        structured: { summary: '', hazards: [], zones: [], actions: [] },
        degraded: true,
        reason: 'Voice handover upload failed.',
        provider: 'speechmatics',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleSignOff = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!logText.trim()) return;

    setSubmitting(true);
    try {
      if (!voiceResult && !audioFile) {
        const wav = textToHandoverWav(logText.trim());
        await submitVoiceHandover(wav, 'maya');
      }

      for (const finding of findings) {
        if (finding.state === 'new' || finding.state === 'acknowledged') {
          await transitionFinding(
            finding.findingId,
            'assigned',
            `Shift handover: ${logText.trim()}`,
            'shift-handover',
          );
        }
      }

      setSignedOff(true);
    } catch (err) {
      console.error('[HandoverSignoff]', err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 p-4 h-[calc(100vh-80px)] overflow-y-auto scrollbar select-text text-ink font-sans">
      <div className="flex items-center justify-between border-b border-line pb-3 select-none shrink-0">
        <div className="flex flex-col gap-1">
          <h1 className="text-lg font-bold uppercase font-mono tracking-wide flex items-center gap-2">
            <ArrowRightLeft className="h-5 w-5 text-accent" />
            Shift Handover Console
          </h1>
          <p className="text-xs text-ink-dim font-mono">
            Review open findings, record voice handover, and sign off to the audit ledger.
          </p>
        </div>
      </div>

      {loadError && (
        <div className="bg-imminent/10 border border-imminent/20 text-imminent text-xs p-2.5 rounded flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          {loadError}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="flex flex-col gap-3">
          <span className="text-xs font-mono font-bold text-ink-dim uppercase select-none flex items-center gap-1.5">
            <ClipboardList className="h-4 w-4" />
            Open Findings ({findings.length})
          </span>

          <div className="flex flex-col gap-2.5">
            {findings.map((finding) => (
              <Card key={finding.findingId} className="p-3 border border-line bg-panel-2/30 flex justify-between items-center">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <Badge variant="band" band={finding.leadTimeBand} className="font-mono text-micro font-bold py-0.5">
                      {finding.findingId}
                    </Badge>
                    <span className="text-xs font-bold text-ink">{finding.title}</span>
                  </div>
                  <span className="text-micro font-mono text-ink-dim uppercase">{finding.zoneId}</span>
                </div>
                <Badge variant="generic" color="near" className="uppercase text-micro scale-90">
                  {finding.state}
                </Badge>
              </Card>
            ))}
            {findings.length === 0 && !loadError && (
              <p className="text-xs font-mono text-ink-dim uppercase p-4 border border-dashed border-line rounded text-center">
                No open findings to hand over
              </p>
            )}
          </div>
        </div>

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
                Handover logged via voice audit trail and open findings assigned to incoming shift.
              </p>
            </Card>
          ) : (
            <>
              <div className="flex flex-col gap-2 p-3 border border-line rounded bg-panel-2/20">
                <span className="text-micro font-mono font-bold text-ink-dim uppercase flex items-center gap-1.5">
                  <Mic className="h-3.5 w-3.5" />
                  Voice handover (Speechmatics)
                </span>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="audio/*"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) void handleVoiceUpload(file);
                  }}
                />
                <Button
                  variant="secondary"
                  size="sm"
                  type="button"
                  loading={submitting}
                  icon={<Upload className="h-3.5 w-3.5" />}
                  onClick={() => fileInputRef.current?.click()}
                  className="self-start text-micro font-mono uppercase"
                >
                  Upload audio recording
                </Button>
                {voiceResult && (
                  <div className="text-xs font-mono text-ink-dim mt-1 space-y-1">
                    {voiceResult.degraded && voiceResult.reason && (
                      <p className="text-near">Degraded: {voiceResult.reason}</p>
                    )}
                    {voiceResult.structured.hazards.length > 0 && (
                      <p>Hazards: {voiceResult.structured.hazards.join(', ')}</p>
                    )}
                    {voiceResult.auditAppended && (
                      <p className="text-ok">Voice entry appended to audit chain.</p>
                    )}
                  </div>
                )}
              </div>

              <form onSubmit={handleSignOff} className="flex flex-col gap-3">
                <textarea
                  placeholder="Handover summary (typed or populated from voice transcript)..."
                  value={logText}
                  onChange={(e) => setLogText(e.target.value)}
                  className="h-28 p-2.5 rounded border border-line text-xs bg-panel text-ink placeholder:text-ink-dim/40 focus:outline-none select-text leading-relaxed"
                  required
                />

                <Button
                  variant="primary"
                  size="sm"
                  type="submit"
                  loading={submitting}
                  disabled={!logText.trim()}
                  className="uppercase text-micro font-bold h-8 tracking-wider w-36 self-end"
                >
                  Sign Off Shift
                </Button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
