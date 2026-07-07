import { useEffect, useState } from 'react';
import type { RiskFinding } from '@/types';
import { Card, Button } from '@/components/atoms';
import {
  Send,
  MessageSquare,
  AlertTriangle,
  Languages,
} from 'lucide-react';
import { transitionFinding } from '@/api';
import { getAlertPreview } from '@/api/intelligence';
import { dispatchAlert } from '@/api/platform';

interface ResponseOrchestratorProps {
  activeFindings: RiskFinding[];
  onChange: () => void;
}

const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'Hindi (हिन्दी)' },
  { code: 'ta', label: 'Tamil (தமிழ்)' },
  { code: 'te', label: 'Telugu (తెలుగు)' },
  { code: 'kn', label: 'Kannada (ಕನ್ನಡ)' },
];

const TEMPLATES: Record<string, Record<string, string>> = {
  'gas-leak': {
    en: 'CRITICAL WARNING: Gas leak detected in [Zone]. Evacuate immediately to Mustering Point Alpha.',
    hi: 'महत्वपूर्ण चेतावनी: [Zone] में गैस रिसाव का पता चला है। तुरंत मस्टरिंग पॉइंट अल्फा पर खाली करें।',
    ta: 'முக்கிய எச்சரிக்கை: [Zone] இல் வாயு கசிவு கண்டறியப்பட்டுள்ளது. உடனடியாக மஸ்டரிங் பாயிண்ட் ஆல்பாவுக்கு வெளியேறவும்.',
    te: 'క్లిష్టమైన హెచ్చరిక: [Zone] లో గ్యాస్ లీకేజీ కనుగొనబడింది. వెంటనే మస్టరింగ్ పాయింట్ ఆల్ఫాకు ఖాళీ చేయండి.',
    kn: 'ನಿರ್ಣಾಯಕ ಎಚ್ಚರಿಕೆ: [Zone] ನಲ್ಲಿ ಅನಿಲ ಸೋರಿಕೆ ಪತ್ತೆಯಾಗಿದೆ. ತಕ್ಷಣವೇ ಮಸ್ಟರಿಂಗ್ ಪಾಯಿಂಟ್ ಆಲ್ಫಾಗೆ ಸ್ಥಳಾಂತರಿಸಿ.',
  },
  'fire-risk': {
    en: 'EMERGENCY: Thermal runway convergence in [Zone]. Fire response team dispatched. Standby.',
    hi: 'आपातकालीन: [Zone] में थर्मल रनवे अभिसरण। फायर रिस्पांस टीम रवाना। स्टैंडबाय।',
    ta: 'அவசரகாலம்: [Zone] இல் வெப்ப ஓட்டக் குவிப்பு. தீயணைப்பு படை அனுப்பப்பட்டது. காத்திருக்கவும்.',
    te: 'అత్యవసర పరిస్థితి: [Zone] లో థర్మల్ రన్‌వే కన్వర్జెన్స్. ఫైర్ రెస్పాన్స్ టీమ్ పంపబడింది. స్టాండ్‌బై.',
    kn: 'ತುರ್ತು ಪರಿಸ್ಥಿತಿ: [Zone] ನಲ್ಲಿ ಥರ್ಮಲ್ ರನ್‌ವೇ ಒಮ್ಮುಖ. ಅಗ್ನಿಶಾಮಕ ಸಿಬ್ಬಂದಿ ರವಾನಿಸಲಾಗಿದೆ. ಸಿದ್ಧರಾಗಿರಿ.',
  },
  'confined-space': {
    en: 'ALERT: Unauthorized SIMOPS conflict detected in [Zone]. Halt all hot work operations immediately.',
    hi: 'चेतावनी: [Zone] में अनधिकृत SIMOPS संघर्ष का पता चला। सभी हॉट वर्क संचालन तुरंत रोकें।',
    ta: 'எச்சரிக்கை: [Zone] இல் அங்கீகரிக்கப்படாத SIMOPS மோதல் கண்டறியப்பட்டது. அனைத்து சூடான வேலைகளையும் உடனடியாக நிறுத்தவும்.',
    te: 'హెచ్చరిక: [Zone] లో అనధికార SIMOPS సంఘర్షణ కనుగొనబడింది. అన్ని హాట్ వర్క్ కార్యకలాపాలను వెంటనే నిలిపివేయండి.',
    kn: 'ಎಚ್ಚರಿಕೆ: [Zone] ನಲ್ಲಿ ಅನಧಿಕೃತ SIMOPS ಸಂಘರ್ಷ ಪತ್ತೆಯಾಗಿದೆ. ಎಲ್ಲಾ ಬಿಸಿ ಕೆಲಸದ ಕಾರ್ಯಾಚರಣೆಗಳನ್ನು ತಕ್ಷಣವೇ ನಿಲ್ಲಿಸಿ.',
  },
};

export function ResponseOrchestratorPanel({ activeFindings, onChange }: ResponseOrchestratorProps) {
  // Select imminent findings as candidate triggers
  const imminentFindings = activeFindings.filter((f) => f.leadTimeBand === 'IMMINENT' && f.state !== 'closed' && f.state !== 'resolved');
  
  const [selectedChannels, setSelectedChannels] = useState<string[]>(['sms', 'app']);
  const [selectedTarget, setSelectedTarget] = useState<'role' | 'zone' | 'all'>('zone');
  const [_targetRole, _setTargetRole] = useState('zone-crew');
  const [lang, setLang] = useState('en');
  const [template, setTemplate] = useState('gas-leak');
  const [customText, setCustomText] = useState('');
  const [previewLanguages, setPreviewLanguages] = useState<Record<string, string>>({});
  const [previewDegraded, setPreviewDegraded] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [deliveryStatus, setDeliveryStatus] = useState<Array<{ name: string; channel: string; status: string }>>([]);

  const trigger = imminentFindings[0];

  useEffect(() => {
    if (!trigger) return;
    let cancelled = false;
    getAlertPreview(trigger.findingId)
      .then((preview) => {
        if (!cancelled) {
          setPreviewLanguages(preview.languages);
          setPreviewDegraded(preview.degraded);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setPreviewLanguages({});
          setPreviewDegraded(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [trigger?.findingId]);

  if (imminentFindings.length === 0 || !trigger) return null;

  const handleChannelToggle = (channel: string) => {
    setSelectedChannels((prev) =>
      prev.includes(channel) ? prev.filter((c) => c !== channel) : [...prev, channel]
    );
  };

  const getMessageBody = () => {
    if (customText) return customText;
    if (previewLanguages[lang]) return previewLanguages[lang];
    const body = TEMPLATES[template]?.[lang] || '';
    return body.replace('[Zone]', trigger.zoneId);
  };

  const handleDispatch = async () => {
    setIsSending(true);
    try {
      const channels = ['console', ...selectedChannels];
      const receipt = await dispatchAlert(trigger.findingId, {
        approvedBy: 'Shift Supervisor Sarah',
        channels,
        action: getMessageBody(),
        languages: [lang],
      });

      if (receipt.refused) {
        setDeliveryStatus([
          {
            name: 'Dispatch refused',
            channel: 'policy',
            status: receipt.reason ?? 'Approver required (P8)',
          },
        ]);
        return;
      }

      await transitionFinding(
        trigger.findingId,
        'escalated',
        `Emergency alerts dispatched for ${trigger.zoneId} via ${channels.join(', ')}`,
        'emergency-dispatch',
      );

      setDeliveryStatus(
        (receipt.results ?? []).map((c) => ({
          name: c.channel.toUpperCase(),
          channel: c.channel,
          status: c.delivered ? 'Delivered' : c.degraded ? `Degraded: ${c.reason ?? ''}` : 'Pending',
        })),
      );

      onChange();
    } catch (err) {
      console.error('[ResponseOrchestrator] Alert failed:', err);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <Card className="border-imminent/40 bg-imminent/5 p-4 flex flex-col gap-4 text-ink select-none shrink-0">
      {/* URGENCE WARNING BANNER */}
      <div className="flex items-start gap-2 border-b border-imminent/20 pb-3">
        <AlertTriangle className="h-5 w-5 text-imminent shrink-0 animate-pulse mt-0.5" />
        <div className="flex flex-col gap-0.5">
          <span className="text-xs font-mono font-bold text-imminent tracking-wider uppercase">
            IMMINENT HAZARD THREAT TRIGGERED
          </span>
          <p className="text-xs text-ink-dim leading-relaxed">
            Finding <code className="text-imminent font-bold">{trigger.findingId}</code> ({trigger.title}) in <span className="font-semibold text-ink">{trigger.zoneId}</span> has reached IMMINENT breach status (threshold forecast &lt;15m). Actuate response loop.
          </p>
        </div>
      </div>

      {/* Main Orchestration inputs grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Column 1: Evac Targets & Channels */}
        <div className="flex flex-col gap-3 border-r border-line/45 pr-4">
          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-semibold text-ink-dim uppercase">1. Channels</span>
            <div className="flex flex-col gap-2">
              {['sms', 'ivr', 'pa', 'app'].map((c) => (
                <button
                  key={c}
                  onClick={() => handleChannelToggle(c)}
                  className={`flex items-center justify-between p-2 rounded border text-xs font-bold font-mono transition-all cursor-pointer ${
                    selectedChannels.includes(c)
                      ? 'bg-imminent/10 border-imminent/30 text-imminent'
                      : 'bg-panel-2 border-line text-ink-dim hover:text-ink'
                  }`}
                >
                  <span className="uppercase">{c === 'app' ? 'Mobile Push' : c === 'pa' ? 'PA Address' : c === 'ivr' ? 'IVR Call' : 'SMS Alert'}</span>
                  <input
                    type="checkbox"
                    checked={selectedChannels.includes(c)}
                    readOnly
                    className="h-3 w-3 rounded text-imminent bg-bg border-line focus:ring-0 focus:ring-offset-0 pointer-events-none"
                  />
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-1.5 mt-1">
            <span className="text-xs font-semibold text-ink-dim uppercase">2. Targets</span>
            <div className="grid grid-cols-3 gap-1">
              {['zone', 'role', 'all'].map((target) => (
                <button
                  key={target}
                  onClick={() => setSelectedTarget(target as any)}
                  className={`h-7 rounded border text-xs font-bold font-mono uppercase cursor-pointer ${
                    selectedTarget === target
                      ? 'bg-imminent/10 border-imminent/30 text-imminent'
                      : 'bg-panel-2 border-line text-ink-dim hover:text-ink'
                  }`}
                >
                  {target}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Column 2: Template Selection & Preview */}
        <div className="flex flex-col gap-3 border-r border-line/45 pr-4">
          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-semibold text-ink-dim uppercase flex items-center gap-1">
              <MessageSquare className="h-3.5 w-3.5" />
              3. Advisory Message
            </span>
            <select
              value={template}
              onChange={(e) => {
                setTemplate(e.target.value);
                setCustomText('');
              }}
              className="h-8 px-2 rounded border border-line text-xs bg-panel-2 text-ink focus:outline-none"
            >
              <option value="gas-leak">Gas Leak Evacuation Advisory</option>
              <option value="fire-risk">Bearing Thermal Advisory</option>
              <option value="confined-space">SIMOPS Halt Operations</option>
            </select>
          </div>

          {/* Translation selector */}
          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-semibold text-ink-dim uppercase flex items-center gap-1">
              <Languages className="h-3.5 w-3.5" />
              Language Dispatch
            </span>
            <div className="grid grid-cols-5 gap-1">
              {LANGUAGES.map((langObj) => (
                <button
                  key={langObj.code}
                  onClick={() => setLang(langObj.code)}
                  className={`h-6 rounded border text-micro font-mono font-bold cursor-pointer uppercase ${
                    lang === langObj.code
                      ? 'bg-imminent/10 border-imminent/30 text-imminent'
                      : 'bg-panel-2 border-line text-ink-dim hover:text-ink'
                  }`}
                  title={langObj.label}
                >
                  {langObj.code}
                </button>
              ))}
            </div>
          </div>

          {/* Text preview */}
          <div className="flex flex-col gap-1 mt-1">
            <span className="text-micro font-mono text-ink-dim uppercase">
              Message Preview {previewDegraded ? '(template fallback)' : '(API draft)'}
            </span>
            <div className="bg-bg border border-line p-2 rounded text-xs text-ink-dim leading-relaxed h-16 overflow-y-auto select-text font-mono">
              {getMessageBody()}
            </div>
          </div>
        </div>

        {/* Column 3: Dispatch triggers and Delivery list */}
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-semibold text-ink-dim uppercase">4. Dispatch Command</span>
            <Button
              variant="danger"
              size="lg"
              loading={isSending}
              onClick={handleDispatch}
              icon={<Send className="h-4 w-4" />}
              className="w-full text-xs font-bold font-mono tracking-wider uppercase h-10 border-imminent/40"
            >
              DISPATCH MASS EMERGENCY ALERTS
            </Button>
          </div>

          {/* Evacuation headcount mustering status */}
          <div className="border border-line bg-panel-2/30 p-2.5 rounded flex flex-col gap-1 text-xs">
            <div className="flex justify-between items-center text-ink-dim font-mono text-micro uppercase">
              <span>Evacuation Mustering (Alpha)</span>
              <span className="text-ok font-bold tabular-nums">42/43 reconciled</span>
            </div>
            <div className="h-1.5 w-full bg-bg border border-line rounded-full overflow-hidden">
              <div className="h-full bg-ok w-[97%]" />
            </div>
          </div>

          {/* Mock delivery tracking logs */}
          {deliveryStatus.length > 0 && (
            <div className="flex flex-col gap-1.5 max-h-[100px] overflow-y-auto border border-line rounded p-2 select-text font-mono text-micro bg-bg/50">
              {deliveryStatus.map((d, idx) => (
                <div key={idx} className="flex justify-between items-center text-ink-dim border-b border-line/20 pb-1">
                  <span>{d.name}</span>
                  <div className="flex items-center gap-1.5">
                    <span className="text-ink-dim/50 uppercase">[{d.channel}]</span>
                    <span className="text-ok">{d.status}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
