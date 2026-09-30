import assert from 'node:assert/strict';
import { VALIDATION_FEED_DESCRIPTION } from '@/lib/validationFeedPresentation';

assert.equal(
  VALIDATION_FEED_DESCRIPTION,
  'Deterministic arithmetic checks detecting calculation discrepancies (> 5%) and unit conversion anomalies.',
);
assert.equal(VALIDATION_FEED_DESCRIPTION.includes('\\%'), false);
assert.equal(VALIDATION_FEED_DESCRIPTION.includes('$'), false);
