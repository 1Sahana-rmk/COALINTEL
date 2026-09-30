export const DOCUMENT_POLL_INTERVAL_MS = 3000;

export interface PollableDocument {
  status?: string | null;
  processing_status?: string | null;
  total_pages?: number | null;
}

const TERMINAL_DOCUMENT_STATUSES = new Set(['PARSED', 'INDEXED', 'FAILED']);
const TERMINAL_PROCESSING_STATES = new Set([
  'READY',
  'REVIEW_RECOMMENDED',
  'VALIDATION_WARNING',
  'DOWNLOAD_FAILED',
  'OCR_FAILED',
  'EXTRACTION_FAILED',
  'UNSUPPORTED_FORMAT',
]);

/**
 * Poll until the authoritative document state is terminal. A PARSED legacy
 * status can briefly coexist with VALIDATING, so canonical processing state is
 * considered before stopping.
 */
export const shouldContinueDocumentPolling = (
  document?: Pick<PollableDocument, 'status' | 'processing_status'> | null,
): boolean => {
  if (!document?.status) return true;
  if (!TERMINAL_DOCUMENT_STATUSES.has(document.status)) return true;
  if (document.status === 'FAILED' || document.status === 'INDEXED') return false;
  // PARSED without a canonical processing state is a legacy terminal result;
  // do not keep a page polling forever because an optional field is absent.
  if (!document.processing_status) return false;
  return !TERMINAL_PROCESSING_STATES.has(document.processing_status);
};

export const liveReadConfig = (cacheBust: number = Date.now()) => ({
  params: { _coalintel_live: cacheBust },
  headers: {
    'Cache-Control': 'no-cache, no-store, max-age=0',
    Pragma: 'no-cache',
  },
});

/** Prefer the backend's authoritative count once parsing has produced it. */
export const getDocumentPageCount = (
  document?: Pick<PollableDocument, 'total_pages'> | null,
  loadedPageCount = 0,
): number => {
  if (document?.total_pages && document.total_pages > 0) return document.total_pages;
  return loadedPageCount > 0 ? loadedPageCount : 1;
};
