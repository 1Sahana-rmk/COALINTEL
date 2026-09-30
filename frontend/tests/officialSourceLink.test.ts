import assert from 'node:assert/strict';
import { buildOfficialSourceUrl } from '../lib/officialSourceLink';

const officialPdf = {
  source_type: 'OFFICIAL',
  source_url: 'https://coal.nic.in/sites/default/files/report.pdf',
  file_type: 'PDF',
} as const;

assert.equal(buildOfficialSourceUrl(officialPdf), 'https://coal.nic.in/sites/default/files/report.pdf');
assert.equal(
  buildOfficialSourceUrl(officialPdf, 17),
  'https://coal.nic.in/sites/default/files/report.pdf#page=17',
);
assert.equal(
  buildOfficialSourceUrl({ ...officialPdf, file_type: 'DOCX' }, 17),
  'https://coal.nic.in/sites/default/files/report.pdf',
  'non-PDF sources must not receive a PDF page fragment',
);
assert.equal(
  buildOfficialSourceUrl({ source_type: 'MANUAL', source_url: officialPdf.source_url, file_type: 'PDF' }),
  null,
  'manual uploads must not be presented as official source links',
);
assert.equal(
  buildOfficialSourceUrl({ source_type: 'OFFICIAL', source_url: null, file_type: 'PDF' }),
  null,
  'missing source URL must remain unavailable',
);
assert.equal(
  buildOfficialSourceUrl({ source_type: 'OFFICIAL', source_url: 'javascript:alert(1)', file_type: 'PDF' }),
  null,
  'unsafe URL schemes must be rejected',
);
assert.equal(
  buildOfficialSourceUrl({ source_type: 'OFFICIAL', source_url: 'https://user:pass@example.gov/report.pdf', file_type: 'PDF' }),
  null,
  'credential-bearing URLs must be rejected',
);

console.log('official source link acceptance tests passed');
