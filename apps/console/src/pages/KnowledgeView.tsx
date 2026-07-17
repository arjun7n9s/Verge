import { useEffect, useState } from 'react';
import { Button, Card, EmptyState } from '@/components/atoms';
import { BookOpen, Upload, Search } from 'lucide-react';
import {
  askKnowledge,
  ingestDocument,
  listDocuments,
  type KnowledgeCitation,
  type KnowledgeDocument,
} from '@/api/knowledge';

export default function KnowledgeView() {
  const [docs, setDocs] = useState<KnowledgeDocument[]>([]);
  const [query, setQuery] = useState('');
  const [answer, setAnswer] = useState('');
  const [citations, setCitations] = useState<KnowledgeCitation[]>([]);
  const [degraded, setDegraded] = useState(false);
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    try {
      const res = await listDocuments();
      setDocs(res.documents);
      setError(null);
    } catch {
      setError('Knowledge API unavailable — start API with `make dev`.');
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const onUpload = async (file: File | null) => {
    if (!file) return;
    setBusy(true);
    try {
      await ingestDocument(file, file.name);
      await refresh();
    } catch {
      setError('Ingest failed.');
    } finally {
      setBusy(false);
    }
  };

  const onAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setBusy(true);
    try {
      const res = await askKnowledge(query.trim());
      setAnswer(res.answer);
      setCitations(res.citations);
      setDegraded(res.degraded);
      setReason(res.reason);
      setError(null);
    } catch {
      setError('Ask failed.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-4 p-4 h-[calc(100vh-80px)] overflow-hidden text-ink">
      <div className="flex items-end justify-between border-b border-line pb-3 shrink-0">
        <div className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold tracking-tight flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-accent" />
            Living Knowledge
          </h1>
          <p className="text-xs text-ink-dim">
            Ingest SOPs, work orders, and procedures — ask with citations. Empty corpus stays empty.
          </p>
        </div>
        <label className="inline-flex">
          <input
            type="file"
            className="hidden"
            onChange={(e) => void onUpload(e.target.files?.[0] ?? null)}
          />
          <Button
            variant="secondary"
            size="sm"
            icon={<Upload className="h-3.5 w-3.5" />}
            loading={busy}
            onClick={(ev) => {
              const input = (ev.currentTarget.parentElement as HTMLLabelElement).querySelector(
                'input',
              );
              input?.click();
            }}
          >
            Ingest document
          </Button>
        </label>
      </div>

      {error && (
        <div className="text-xs text-imminent border border-imminent/30 bg-imminent/5 p-2 rounded">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 min-h-0 flex-1">
        <Card className="lg:col-span-2 p-3 flex flex-col gap-2 min-h-0 overflow-hidden">
          <span className="text-micro font-mono text-ink-dim uppercase tracking-[0.1em]">
            Corpus · {docs.length}
          </span>
          <div className="flex-1 overflow-y-auto flex flex-col gap-2">
            {docs.length === 0 ? (
              <EmptyState
                icon={<BookOpen className="h-5 w-5" />}
                title="No documents yet"
                hint="Upload a .md / .txt SOP to start. Verge will not invent a library."
              />
            ) : (
              docs.map((d) => (
                <div
                  key={d.documentId}
                  className="border border-line rounded p-2.5 text-xs flex flex-col gap-1"
                >
                  <div className="flex justify-between gap-2">
                    <span className="font-semibold truncate">{d.title}</span>
                    <span className="font-mono text-micro text-ink-dim shrink-0">
                      {d.kind}
                    </span>
                  </div>
                  <span className="font-mono text-micro text-ink-dim">
                    {d.status} · {d.textChars} chars · {d.documentId}
                  </span>
                </div>
              ))
            )}
          </div>
        </Card>

        <Card className="lg:col-span-3 p-3 flex flex-col gap-3 min-h-0 overflow-hidden">
          <form onSubmit={onAsk} className="flex gap-2 shrink-0">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. What must be checked before hot work in B-04?"
              className="flex-1 h-9 px-3 rounded border border-line bg-panel text-sm text-ink placeholder:text-ink-dim/40 focus:outline-none focus:border-accent"
            />
            <Button
              type="submit"
              variant="primary"
              size="sm"
              loading={busy}
              icon={<Search className="h-3.5 w-3.5" />}
            >
              Ask
            </Button>
          </form>

          <div className="flex-1 overflow-y-auto flex flex-col gap-3">
            {answer ? (
              <div className="border border-line rounded p-3 text-sm leading-relaxed whitespace-pre-wrap">
                {answer}
                {degraded && (
                  <p className="mt-2 text-micro font-mono text-ink-dim">
                    Degraded · {reason || 'partial'}
                  </p>
                )}
              </div>
            ) : (
              <EmptyState
                title="Ask the plant corpus"
                hint="Answers are grounded in ingested chunks with citations — or honestly empty."
              />
            )}

            {citations.length > 0 && (
              <div className="flex flex-col gap-2">
                <span className="text-micro font-mono text-ink-dim uppercase tracking-[0.1em]">
                  Citations
                </span>
                {citations.map((c, i) => (
                  <div key={c.chunkId} className="border border-line rounded p-2.5 text-xs">
                    <div className="font-mono text-micro text-ink-dim mb-1">
                      [{i + 1}] {c.title} · score {c.score}
                    </div>
                    <p className="text-ink-dim leading-relaxed">{c.excerpt}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
