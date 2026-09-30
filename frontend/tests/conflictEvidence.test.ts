import assert from 'node:assert/strict';
import { buildConflictEvidenceUrl, evidenceLinkLabel } from '../lib/conflictEvidence';

const pageOne = {
  document_id: 66,
  metric_id: 7001,
  page_number: 1,
  provenance_available: true,
  bounding_box: null,
};
const laterPage = {
  document_id: 64,
  metric_id: 7002,
  page_number: 7,
  provenance_available: true,
  bounding_box: null,
};

assert.equal(buildConflictEvidenceUrl(66, pageOne), '/documents/66?page=1&evidence=7001');
assert.equal(buildConflictEvidenceUrl(64, laterPage), '/documents/64?page=7&evidence=7002');
assert.equal(evidenceLinkLabel(pageOne), 'View Evidence · Page 1');
assert.equal(evidenceLinkLabel(laterPage), 'View Evidence · Page 7');
assert.equal(
  buildConflictEvidenceUrl(10, {
    document_id: 10,
    metric_id: 7100,
    page_number: null,
    provenance_available: false,
    bounding_box: null,
  }),
  '/documents/10?evidence=7100',
);
assert.equal(
  buildConflictEvidenceUrl(10, {
    document_id: 10,
    metric_id: 7101,
    page_number: 0,
    provenance_available: false,
    bounding_box: null,
  }),
  '/documents/10?evidence=7101',
  'invalid zero-based page values must not be sent as workspace page numbers',
);
assert.equal(buildConflictEvidenceUrl(null, null), null);

console.log('conflict evidence deep-link acceptance tests passed');
