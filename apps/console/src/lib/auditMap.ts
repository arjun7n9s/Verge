import type { AuditEntryWire } from '@/api/audit';

export interface AuditRow {
  index: number;
  entryId: string;
  hash: string;
  prevHash: string;
  timestamp: string;
  actor: string;
  eventType: string;
  details: string;
  isValid: boolean;
}

function formatDetails(entry: AuditEntryWire): string {
  const p = entry.payload;
  if (typeof p.findingId === 'string') {
    const parts = [entry.kind, p.findingId];
    if (typeof p.to === 'string') parts.push(`→ ${p.to}`);
    if (typeof p.verdict === 'string') parts.push(`(${p.verdict})`);
    return parts.join(' ');
  }
  if (typeof p.kind === 'string') return `${entry.kind}: ${p.kind}`;
  return `${entry.kind} · ${JSON.stringify(p)}`;
}

/** Map API audit entries to UI rows with prev-hash linkage checks. */
export function mapAuditEntries(entries: AuditEntryWire[]): AuditRow[] {
  const chronological = [...entries].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  );

  const rows: AuditRow[] = [];
  let prevHash = '0'.repeat(64);

  for (let i = 0; i < chronological.length; i++) {
    const entry = chronological[i];
    const linked = entry.prevHash === prevHash;
    rows.push({
      index: i + 1,
      entryId: entry.entryId,
      hash: entry.hash,
      prevHash: entry.prevHash,
      timestamp: entry.timestamp,
      actor: entry.actor,
      eventType: entry.kind,
      details: formatDetails(entry),
      isValid: linked,
    });
    prevHash = entry.hash;
  }

  return rows.reverse();
}

/** Audit rows for a single finding (subset — linkage not re-verified). */
export function auditRowsForFinding(entries: AuditEntryWire[], findingId: string): AuditRow[] {
  const matches = entries.filter((entry) => entry.payload?.findingId === findingId);
  const chronological = [...matches].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  );

  return chronological
    .map((entry, i) => ({
      index: i + 1,
      entryId: entry.entryId,
      hash: entry.hash,
      prevHash: entry.prevHash,
      timestamp: entry.timestamp,
      actor: entry.actor,
      eventType: entry.kind,
      details: formatDetails(entry),
      isValid: true,
    }))
    .reverse();
}
