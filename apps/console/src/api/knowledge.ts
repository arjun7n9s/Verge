import { request } from './client';

export interface KnowledgeDocument {
  documentId: string;
  title: string;
  kind: string;
  status: string;
  sourceName: string;
  mimeType: string;
  pageCount: number;
  textChars: number;
  createdAt: string;
  error?: string | null;
  plantPack?: string | null;
}

export interface KnowledgeCitation {
  documentId: string;
  title: string;
  chunkId: string;
  page: number | null;
  excerpt: string;
  score: number;
}

export interface KnowledgeAskResult {
  answer: string;
  citations: KnowledgeCitation[];
  degraded: boolean;
  reason: string;
}

export async function listDocuments(signal?: AbortSignal): Promise<{
  documents: KnowledgeDocument[];
  count: number;
}> {
  return request('/api/docs', { signal });
}

export async function ingestDocument(file: File, title?: string): Promise<{
  document: KnowledgeDocument;
  entityCount: number;
  chunkCount: number;
}> {
  const form = new FormData();
  form.append('file', file);
  if (title) form.append('title', title);
  return request('/api/docs/ingest', { method: 'POST', body: form });
}

export async function askKnowledge(
  query: string,
  signal?: AbortSignal,
): Promise<KnowledgeAskResult> {
  return request('/api/knowledge/ask', {
    method: 'POST',
    body: JSON.stringify({ query }),
    signal,
  });
}
