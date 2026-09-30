import assert from 'node:assert/strict';
import {
  getParliamentaryErrorMessage,
  getParliamentaryExportErrorMessage,
} from '../lib/parliamentaryError';

assert.equal(
  getParliamentaryErrorMessage({ code: 'ECONNABORTED', message: 'timeout of 15000ms exceeded' }),
  'Briefing generation could not complete within the allowed time.',
);
assert.equal(
  getParliamentaryErrorMessage({ response: { data: { detail: 'embedding service unavailable' } } }),
  'Semantic evidence retrieval is currently unavailable.',
);
assert.equal(
  getParliamentaryErrorMessage({ response: { data: { detail: 'safe backend detail' } } }),
  'safe backend detail',
);
assert.equal(
  getParliamentaryExportErrorMessage({ code: 'ECONNABORTED', message: 'timeout of 15000ms exceeded' }),
  'Briefing PDF export could not complete within the allowed time.',
);
assert.equal(
  getParliamentaryExportErrorMessage({ response: { data: { detail: 'Parliamentary briefing PDF generation failed.' } } }),
  'Parliamentary briefing PDF generation failed.',
);

console.log('parliamentary error presentation assertions passed');
