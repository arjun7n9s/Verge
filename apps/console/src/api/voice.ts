export interface VoiceStructured {
  summary: string;
  hazards: string[];
  zones: string[];
  actions: string[];
}

export interface VoiceResult {
  transcript: string;
  structured: VoiceStructured;
  degraded: boolean;
  reason?: string;
  provider: string;
  jobId?: string;
  auditAppended?: boolean;
}

async function postVoiceForm(path: string, file: File, actor: string): Promise<VoiceResult> {
  const form = new FormData();
  form.append('file', file, file.name);
  form.append('actor', actor);

  const response = await fetch(path, { method: 'POST', body: form });
  if (!response.ok) {
    const body = await response.text().catch(() => '');
    throw new Error(`Voice request failed: ${response.status} ${body}`);
  }
  return (await response.json()) as VoiceResult;
}

export async function transcribeVoice(file: File): Promise<VoiceResult> {
  return postVoiceForm('/api/voice/transcribe', file, 'maya');
}

export async function submitVoiceHandover(file: File, actor = 'maya'): Promise<VoiceResult> {
  return postVoiceForm('/api/voice/handover', file, actor);
}

/** Build a minimal WAV blob from browser speech-capture text for handover audit trail. */
export function textToHandoverWav(text: string): File {
  const sampleRate = 8000;
  const durationSec = Math.min(3, Math.max(1, text.length / 40));
  const numSamples = Math.floor(sampleRate * durationSec);
  const buffer = new ArrayBuffer(44 + numSamples * 2);
  const view = new DataView(buffer);

  const writeStr = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
  };

  writeStr(0, 'RIFF');
  view.setUint32(4, 36 + numSamples * 2, true);
  writeStr(8, 'WAVE');
  writeStr(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeStr(36, 'data');
  view.setUint32(40, numSamples * 2, true);

  return new File([buffer], 'handover-note.wav', { type: 'audio/wav' });
}
