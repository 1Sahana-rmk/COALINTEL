import assert from 'node:assert/strict';
import {
  getDocumentPageCount,
  liveReadConfig,
  shouldContinueDocumentPolling,
} from '../lib/documentPolling';

const processing = { status: 'PROCESSING', processing_status: 'EXTRACTING' };
const parsed = { status: 'PARSED', processing_status: 'READY' };
const review = { status: 'PARSED', processing_status: 'REVIEW_RECOMMENDED' };

assert.equal(shouldContinueDocumentPolling(processing), true, 'PROCESSING must continue polling');
assert.equal(shouldContinueDocumentPolling(parsed), false, 'PARSED/READY must stop polling');
assert.equal(shouldContinueDocumentPolling({ status: 'PARSED' }), false, 'legacy PARSED without processing state must stop polling');
assert.equal(shouldContinueDocumentPolling(review), false, 'REVIEW_RECOMMENDED must stop polling');
assert.equal(
  shouldContinueDocumentPolling({ status: 'FAILED', processing_status: 'EXTRACTION_FAILED' }),
  false,
  'FAILED must stop polling',
);

assert.equal(getDocumentPageCount({ total_pages: 1 }, 0), 1, 'temporary upload count is retained until authoritative data exists');
assert.equal(getDocumentPageCount({ total_pages: 83 }, 1), 83, 'authoritative page count replaces temporary count');
assert.equal(getDocumentPageCount({ total_pages: null }, 7), 7, 'loaded page records are a safe fallback');

const requestConfig = liveReadConfig(123456);
assert.equal(requestConfig.params._coalintel_live, 123456, 'live reads carry a deterministic cache-busting value');
assert.equal(requestConfig.headers['Cache-Control'], 'no-cache, no-store, max-age=0');
assert.equal(requestConfig.headers.Pragma, 'no-cache');

console.log('documentPolling acceptance tests passed');
