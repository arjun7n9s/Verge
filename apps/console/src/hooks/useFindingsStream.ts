import { useEffect, useRef } from 'react';
import { createSSEConnection } from '@/api';
import type { RiskFinding } from '@/types';

/** Subscribe to /api/stream SSE when enabled; caller handles poll fallback on error. */
export function useFindingsStream(
  enabled: boolean,
  onFindings: (findings: RiskFinding[]) => void,
  onError?: () => void,
) {
  const onFindingsRef = useRef(onFindings);
  onFindingsRef.current = onFindings;
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;

  useEffect(() => {
    if (!enabled) return;

    let closed = false;
    const source = createSSEConnection('/api/stream', {
      onMessage: (data) => {
        if (Array.isArray(data)) {
          onFindingsRef.current(data as RiskFinding[]);
        }
      },
      onError: () => {
        if (!closed) onErrorRef.current?.();
      },
    });

    return () => {
      closed = true;
      source.close();
    };
  }, [enabled]);
}
