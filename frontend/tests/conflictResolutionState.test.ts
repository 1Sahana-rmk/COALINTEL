import assert from 'node:assert/strict';
import {
  canSubmitConflictResolution,
  formatConflictDocumentIdentifier,
  isResolvedConflict,
} from '../lib/conflictResolutionState';

assert.equal(isResolvedConflict('RESOLVED'), true);
assert.equal(isResolvedConflict('OPEN'), false);
assert.equal(canSubmitConflictResolution('OPEN', false), true);
assert.equal(canSubmitConflictResolution('OPEN', true), false, 'pending submission blocks duplicate clicks');
assert.equal(canSubmitConflictResolution('RESOLVED', false), false, 'resolved conflict cannot be submitted again');

assert.equal(formatConflictDocumentIdentifier(161, null), 'ID #161');
assert.equal(
  formatConflictDocumentIdentifier(null, 'MOC-CD-2024-25'),
  'Source MOC-CD-2024-25',
  'catalog/source identifiers must not be rendered as ID #0',
);
assert.equal(formatConflictDocumentIdentifier(null, null), 'Identifier unavailable');

console.log('conflictResolutionState acceptance tests passed');
