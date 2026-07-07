import { useState } from 'react';
import type { RiskFinding } from '@/types';
import { Button } from '@/components/atoms';
import { Download, AlertCircle } from 'lucide-react';
import { getIncidentReport } from '@/api/platform';

interface ExportIncidentReportButtonProps {
  finding: RiskFinding;
}

export function ExportIncidentReportButton({ finding }: ExportIncidentReportButtonProps) {
  const [isExporting, setIsExporting] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  const handleExport = async () => {
    setIsExporting(true);
    setNote(null);
    try {
      const report = await getIncidentReport(finding.findingId);
      const dataStr =
        'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(report, null, 2));
      const anchor = document.createElement('a');
      anchor.setAttribute('href', dataStr);
      anchor.setAttribute('download', `incident-report-${finding.findingId}.json`);
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
    } catch {
      setNote('Incident report API unavailable — start backend with `make dev`.');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="flex flex-col gap-1.5">
      <Button
        variant="secondary"
        size="sm"
        onClick={handleExport}
        loading={isExporting}
        icon={<Download className="h-3.5 w-3.5 text-accent" />}
        className="text-micro font-mono font-bold uppercase"
      >
        Export Incident Report
      </Button>
      {note && (
        <span className="text-micro text-ink-dim font-mono flex items-start gap-1">
          <AlertCircle className="h-3 w-3 shrink-0 mt-0.5" />
          {note}
        </span>
      )}
    </div>
  );
}
