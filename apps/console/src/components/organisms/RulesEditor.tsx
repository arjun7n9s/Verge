import { useState } from 'react';
import { Card, Button } from '@/components/atoms';
import { Play, CheckCircle, AlertTriangle, Code } from 'lucide-react';

interface RuleDSL {
  name: string;
  code: string;
  isActive: boolean;
  version: number;
}

const INITIAL_RULES: RuleDSL[] = [
  {
    name: 'ReformerThermalRisk',
    code: `rule ReformerThermalRisk {
  select temp = TEMP-0411, methane = CH4-0412
  when temp > 80C and methane > 1.0% LEL
  trigger IMMINENT "Potential Reformer gas leak ignition risk"
}`,
    isActive: true,
    version: 1,
  },
  {
    name: 'StoragePressureRisk',
    code: `rule StoragePressureRisk {
  select pressure = PRES-0211
  when pressure < 0.8bar
  trigger WATCH "Purge pressure decline in dikes"
}`,
    isActive: true,
    version: 3,
  },
];

export function RulesEditor() {
  const [rules, setRules] = useState<RuleDSL[]>(INITIAL_RULES);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [code, setCode] = useState(rules[0].code);
  const [compileStatus, setCompileStatus] = useState<{ status: 'ok' | 'error'; text: string } | null>(null);

  const activeRule = rules[selectedIdx];

  const handleRuleSelect = (idx: number) => {
    setSelectedIdx(idx);
    setCode(rules[idx].code);
    setCompileStatus(null);
  };

  const handleCodeChange = (newCode: string) => {
    setCode(newCode);
  };

  const handleCompile = () => {
    // Validate rules parser tokens: rule, select, when, trigger
    const tokens = ['rule', 'select', 'when', 'trigger'];
    const missing = tokens.filter((tok) => !code.toLowerCase().includes(tok));

    if (missing.length > 0) {
      setCompileStatus({
        status: 'error',
        text: `DSL Syntax Error: Missing structural keyword(s) [${missing.join(', ')}].`,
      });
      return;
    }

    setCompileStatus({
      status: 'ok',
      text: 'DSL Compilation Successful: Safety rule successfully verified and scheduled.',
    });

    // Update rules store
    setRules((prev) =>
      prev.map((r, idx) =>
        idx === selectedIdx ? { ...r, code, version: r.version + 1 } : r
      )
    );
  };

  const toggleRuleActive = () => {
    setRules((prev) =>
      prev.map((r, idx) =>
        idx === selectedIdx ? { ...r, isActive: !r.isActive } : r
      )
    );
  };

  return (
    <Card className="p-3 bg-panel border-line text-ink font-mono text-xs select-none">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-2.5 mb-3 select-none">
        <span className="font-bold text-ink-dim uppercase flex items-center gap-1.5">
          <Code className="h-4 w-4" />
          Safety Rules DSL Workspace
        </span>

        {/* Dropdown scenario select */}
        <div className="flex items-center gap-2 text-micro">
          <span className="text-ink-dim uppercase">TARGET RULE:</span>
          <select
            value={selectedIdx}
            onChange={(e) => handleRuleSelect(parseInt(e.target.value))}
            className="h-7 px-2 rounded border border-line bg-panel-2 text-ink focus:outline-none"
          >
            {rules.map((r, idx) => (
              <option key={idx} value={idx}>
                {r.name} (v{r.version})
              </option>
            ))}
          </select>

          <button
            onClick={toggleRuleActive}
            className={`h-7 px-2.5 rounded border text-[10px] font-bold cursor-pointer transition-colors uppercase ${
              activeRule.isActive
                ? 'bg-ok/20 border-ok/40 text-ok'
                : 'bg-imminent/10 border-imminent/30 text-imminent'
            }`}
          >
            {activeRule.isActive ? 'Active' : 'Disabled'}
          </button>
        </div>
      </div>

      {/* Editor & output */}
      <div className="flex flex-col gap-3">
        <div className="relative">
          <textarea
            value={code}
            onChange={(e) => handleCodeChange(e.target.value)}
            className="w-full h-40 p-3 bg-bg border border-line rounded text-xs text-ink placeholder:text-ink-dim/40 font-mono leading-relaxed focus:outline-none select-text"
            spellCheck="false"
          />
          <div className="absolute bottom-2 right-2 flex items-center gap-2 select-none">
            <Button
              variant="primary"
              size="sm"
              onClick={handleCompile}
              icon={<Play className="h-3 w-3" />}
              className="h-6 w-20 text-micro uppercase py-0 bg-accent/25 border-accent/40 text-accent hover:bg-accent/45"
            >
              Verify DSL
            </Button>
          </div>
        </div>

        {/* Syntax verify response log */}
        {compileStatus && (
          <div className={`p-2.5 rounded border text-micro flex items-start gap-2 select-text leading-relaxed ${
            compileStatus.status === 'error'
              ? 'bg-imminent/10 border-imminent/20 text-imminent'
              : 'bg-ok/10 border-ok/20 text-ok'
          }`}>
            {compileStatus.status === 'error' ? (
              <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
            ) : (
              <CheckCircle className="h-4 w-4 shrink-0 mt-0.5" />
            )}
            <div>
              <span className="font-bold">{compileStatus.status === 'error' ? 'COMPILER FAILED:' : 'COMPILED OK:'}</span>
              <p className="mt-0.5">{compileStatus.text}</p>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
