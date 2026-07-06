import { useEffect, useMemo, useState } from 'react';
import { Card, Badge, Button } from '@/components/atoms';
import { ShieldCheck, ShieldAlert, Download, Search, AlertTriangle } from 'lucide-react';
import { getAuditEntries } from '@/api';
import { mapAuditEntries, type AuditRow } from '@/lib/auditMap';

export default function AuditView() {
  const [logs, setLogs] = useState<AuditRow[]>([]);
  const [selectedEntry, setSelectedEntry] = useState<AuditRow | null>(null);
  const [search, setSearch] = useState('');
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadAudit = async () => {
    setLoading(true);
    try {
      const entries = await getAuditEntries(100);
      const rows = mapAuditEntries(entries);
      setLogs(rows);
      setSelectedEntry(rows[0] ?? null);
      setLoadError(null);
    } catch {
      setLogs([]);
      setSelectedEntry(null);
      setLoadError('Audit ledger unavailable — start API with `make dev`.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadAudit();
    const interval = setInterval(loadAudit, 10000);
    return () => clearInterval(interval);
  }, []);

  const filteredLogs = useMemo(() => {
    const q = search.toLowerCase();
    return logs.filter(
      (log) =>
        log.details.toLowerCase().includes(q) ||
        log.hash.toLowerCase().includes(q) ||
        log.eventType.toLowerCase().includes(q),
    );
  }, [logs, search]);

  const handleExportAudit = () => {
    try {
      const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(logs, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute('href', dataStr);
      downloadAnchor.setAttribute('download', 'verge-audit-chain.json');
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
    } catch (err) {
      console.error('[AuditExport] Export failed:', err);
    }
  };

  const handleSimulateDiscontinuity = () => {
    const tamperedEntry: AuditRow = {
      index: (logs[0]?.index ?? 0) + 1,
      entryId: 'AE-TAMPER',
      hash: 'f'.repeat(64),
      prevHash: 'corrupted-hash-link',
      timestamp: new Date().toISOString(),
      actor: 'unknown',
      eventType: 'unauthorized_patch',
      details: 'ATTEMPTED MANIPULATION: Log database entry updated externally',
      isValid: false,
    };
    setLogs((prev) => [tamperedEntry, ...prev]);
    setSelectedEntry(tamperedEntry);
  };

  return (
    <div className="flex flex-col gap-6 p-4 h-[calc(100vh-80px)] overflow-hidden text-ink font-sans">
      <div className="flex items-center justify-between border-b border-line pb-3 select-none shrink-0">
        <div className="flex flex-col gap-1">
          <h1 className="text-lg font-bold uppercase font-mono tracking-wide">
            Audit Ledger Chain Verification
          </h1>
          <p className="text-xs text-ink-dim font-mono">
            Live hash-chain entries from <code className="text-accent">GET /api/audit</code>.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {import.meta.env.DEV && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleSimulateDiscontinuity}
              icon={<AlertTriangle className="h-3.5 w-3.5 text-imminent" />}
              className="text-micro font-mono font-bold uppercase text-ink-dim hover:text-imminent"
            >
              Simulate Tamper
            </Button>
          )}
          <Button
            variant="secondary"
            size="sm"
            onClick={handleExportAudit}
            disabled={logs.length === 0}
            icon={<Download className="h-3.5 w-3.5 text-accent" />}
            className="text-micro font-mono font-bold uppercase"
          >
            Export Ledger
          </Button>
        </div>
      </div>

      {loadError && (
        <div className="bg-imminent/10 border border-imminent/20 text-imminent text-xs rounded p-2.5 flex items-center gap-2 shrink-0">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          {loadError}
        </div>
      )}

      <div className="flex-1 flex flex-col md:flex-row gap-4 overflow-hidden">
        <div className="w-full md:w-2/3 flex flex-col gap-3 overflow-hidden">
          <div className="relative shrink-0 select-none">
            <Search className="absolute left-2.5 top-2 h-4 w-4 text-ink-dim/40" />
            <input
              type="text"
              placeholder="Search logs by hash, event, or keyword description..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full h-8 pl-9 pr-3 rounded border border-line text-xs bg-panel text-ink placeholder:text-ink-dim/40 focus:outline-none"
            />
          </div>

          <div className="flex-1 overflow-y-auto scrollbar border border-line rounded">
            {loading && logs.length === 0 ? (
              <div className="p-6 text-center text-xs font-mono text-ink-dim uppercase animate-pulse">
                Loading audit chain...
              </div>
            ) : (
              <table className="w-full text-left font-mono text-xs select-text">
                <thead className="bg-panel-2/50 border-b border-line text-ink-dim text-micro uppercase select-none">
                  <tr>
                    <th className="p-2.5 w-12">Index</th>
                    <th className="p-2.5 w-32">Event Type</th>
                    <th className="p-2.5">Hash Linkage</th>
                    <th className="p-2.5 w-16 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line/30 bg-bg">
                  {filteredLogs.map((log) => (
                    <tr
                      key={log.entryId}
                      onClick={() => setSelectedEntry(log)}
                      className={`cursor-pointer hover:bg-panel-2/20 transition-colors ${
                        selectedEntry?.entryId === log.entryId ? 'bg-panel-2/50' : ''
                      } ${!log.isValid ? 'bg-imminent/5' : ''}`}
                    >
                      <td className="p-2.5 text-ink-dim">{log.index}</td>
                      <td className="p-2.5 uppercase font-bold text-ink-dim truncate max-w-[120px]">
                        {log.eventType}
                      </td>
                      <td className="p-2.5 truncate max-w-[180px]">{log.hash}</td>
                      <td className="p-2.5 text-center select-none">
                        {log.isValid ? (
                          <ShieldCheck className="h-4 w-4 text-ok mx-auto" />
                        ) : (
                          <ShieldAlert className="h-4 w-4 text-imminent mx-auto animate-pulse" />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="flex-1 flex flex-col gap-3 overflow-hidden select-text">
          <span className="text-xs font-mono font-bold text-ink-dim uppercase select-none">
            Block Properties
          </span>
          {selectedEntry ? (
            <Card
              className={`p-4 border flex flex-col gap-3 h-full overflow-y-auto scrollbar bg-panel ${
                selectedEntry.isValid ? 'border-line' : 'border-imminent/40 bg-imminent/5'
              }`}
            >
              <div className="flex justify-between items-center border-b border-line pb-2 mb-1 shrink-0 select-none">
                <span className="font-bold text-ink font-mono">BLOCK #{selectedEntry.index}</span>
                <Badge
                  variant="generic"
                  color={selectedEntry.isValid ? 'ok' : 'imminent'}
                  className="font-mono text-micro font-bold py-0.5"
                >
                  {selectedEntry.isValid ? 'VERIFIED' : 'INTEGRITY FAILED'}
                </Badge>
              </div>

              <div className="flex flex-col gap-1 font-mono text-xs">
                <span className="text-micro text-ink-dim uppercase select-none">Event Class</span>
                <span className="text-ink font-semibold uppercase">{selectedEntry.eventType}</span>
              </div>

              <div className="flex flex-col gap-1 font-mono text-xs">
                <span className="text-micro text-ink-dim uppercase select-none">Timestamp</span>
                <span className="text-ink">{selectedEntry.timestamp}</span>
              </div>

              <div className="flex flex-col gap-1 font-mono text-xs">
                <span className="text-micro text-ink-dim uppercase select-none">Actor</span>
                <span className="text-ink uppercase">{selectedEntry.actor}</span>
              </div>

              <div className="flex flex-col gap-1 font-mono text-xs">
                <span className="text-micro text-ink-dim uppercase select-none">Transaction Details</span>
                <p className="text-ink leading-relaxed">{selectedEntry.details}</p>
              </div>

              <div className="flex flex-col gap-1 font-mono text-micro text-ink-dim break-all">
                <span className="text-micro text-ink-dim uppercase select-none">BLOCK HASH (SHA-256)</span>
                <span className="bg-bg border border-line p-1.5 rounded">{selectedEntry.hash}</span>
              </div>

              <div className="flex flex-col gap-1 font-mono text-micro text-ink-dim break-all">
                <span className="text-micro text-ink-dim uppercase select-none">PREVIOUS HASH</span>
                <span className="bg-bg border border-line p-1.5 rounded">{selectedEntry.prevHash}</span>
              </div>

              {!selectedEntry.isValid && (
                <div className="bg-imminent/5 border border-imminent/10 p-3 rounded flex items-start gap-2 text-xs text-imminent leading-normal select-none">
                  <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold">Ledger Discontinuity:</span> Previous block hash link is corrupted or missing.
                  </div>
                </div>
              )}
            </Card>
          ) : (
            <div className="flex-1 flex items-center justify-center border border-dashed border-line rounded">
              <span className="text-xs text-ink-dim font-mono uppercase">Select a block to inspect</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
