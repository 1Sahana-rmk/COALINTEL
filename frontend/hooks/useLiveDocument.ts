'use client';

import { useEffect, useState } from 'react';
import { documentApi } from '@/lib/api/documentApi';
import { DOCUMENT_POLL_INTERVAL_MS, shouldContinueDocumentPolling } from '@/lib/documentPolling';
import { DocumentItem } from '@/types/document';

interface LiveDocumentState {
  document: DocumentItem | null;
  isLoading: boolean;
  isError: boolean;
  error: unknown;
}

/**
 * Fetch the authoritative document record and update the rendered state
 * directly. Recursive scheduling avoids overlapping requests and naturally
 * stops after a terminal backend state is observed.
 */
export function useLiveDocument(docId: number): LiveDocumentState {
  const [state, setState] = useState<LiveDocumentState>({
    document: null,
    isLoading: true,
    isError: false,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;
    let latestDocument: DocumentItem | null = null;

    const scheduleNext = (latest: DocumentItem | null) => {
      if (cancelled || !shouldContinueDocumentPolling(latest)) return;
      timer = window.setTimeout(() => {
        void poll();
      }, DOCUMENT_POLL_INTERVAL_MS);
    };

    const poll = async (): Promise<void> => {
      try {
        const latest = await documentApi.getDocumentById(docId, { cacheBust: Date.now() });
        if (cancelled) return;
        latestDocument = latest;
        // This state is the source rendered by DocumentHeaderCard and the page
        // count. React Query remains responsible for associated collections.
        setState({ document: latest, isLoading: false, isError: false, error: null });
        scheduleNext(latest);
      } catch (error) {
        if (cancelled) return;
        setState((previous) => ({ ...previous, isLoading: false, isError: true, error }));
        // A transient read failure must not permanently stop live acceptance
        // polling while the document is still processing.
        scheduleNext(latestDocument);
      }
    };

    setState({ document: null, isLoading: true, isError: false, error: null });
    void poll();

    return () => {
      cancelled = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
    // docId is the only identity this polling lifecycle depends on.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docId]);

  return state;
}
