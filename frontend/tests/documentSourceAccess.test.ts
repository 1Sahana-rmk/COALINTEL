import assert from 'node:assert/strict';
import { getDocumentSourceAction, getDocumentSourceActions } from '../lib/documentSourceAccess';

const base = {
  file_type: 'PDF' as const,
  file_path: 'storage/uploads/hash-report.pdf',
};

assert.deepEqual(
  getDocumentSourceAction({
    ...base,
    source_type: 'OFFICIAL',
    source_url: 'https://coal.nic.in/sites/default/files/report.pdf',
  }, 8),
  { kind: 'official', url: 'https://coal.nic.in/sites/default/files/report.pdf#page=8' },
);
assert.deepEqual(
  getDocumentSourceActions({
    ...base,
    source_type: 'OFFICIAL',
    source_url: 'https://coal.nic.in/sites/default/files/report.pdf',
  }, 8),
  {
    officialUrl: 'https://coal.nic.in/sites/default/files/report.pdf#page=8',
    storedArtifactAvailable: true,
  },
  'official URL and locally ingested artifact must remain separate actions',
);
assert.deepEqual(
  getDocumentSourceAction({ ...base, source_type: 'MANUAL', source_url: null }),
  { kind: 'stored' },
);
assert.deepEqual(
  getDocumentSourceAction({ ...base, file_path: '', source_type: 'MANUAL', source_url: null }),
  { kind: 'unavailable' },
);
assert.deepEqual(
  getDocumentSourceAction({ ...base, source_type: 'OFFICIAL', source_url: 'javascript:alert(1)' }),
  { kind: 'stored' },
  'unsafe official provenance must not become a link; a stored copy remains a distinct fallback',
);

console.log('document source action tests passed');
