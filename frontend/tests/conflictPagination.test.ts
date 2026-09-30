import assert from 'node:assert/strict';
import {
  formatConflictCount,
  getConflictPageSkip,
  getTotalConflictPages,
  validateConflictPageInput,
} from '../lib/conflictPagination';

const totalPages = getTotalConflictPages(65560, 50);
assert.equal(totalPages, 1312);
assert.equal(getConflictPageSkip(500, 50), 24950);
assert.equal(formatConflictCount(65560), '65,560');

assert.equal(validateConflictPageInput('500', totalPages).page, 500);
assert.equal(validateConflictPageInput('1', totalPages).valid, true);
assert.equal(validateConflictPageInput('1312', totalPages).valid, true);
assert.equal(validateConflictPageInput('0', totalPages).valid, false);
assert.equal(validateConflictPageInput('-1', totalPages).valid, false);
assert.equal(validateConflictPageInput('1.5', totalPages).valid, false);
assert.equal(validateConflictPageInput('abc', totalPages).valid, false);
assert.equal(validateConflictPageInput('', totalPages).valid, false);
assert.equal(validateConflictPageInput('1313', totalPages).valid, false);
assert.match(validateConflictPageInput('1313', totalPages).error || '', /1,312/);

console.log('conflict pagination acceptance tests passed');
