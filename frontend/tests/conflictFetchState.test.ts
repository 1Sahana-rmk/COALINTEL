import assert from 'node:assert/strict';
import {
  canRefreshConflictList,
  getConflictListViewState,
  shouldFetchConflictDetail,
  shouldRenderConflictListSkeleton,
} from '../lib/conflictFetchState';

assert.equal(
  shouldFetchConflictDetail({ targetId: '3', listLoading: true, hasListMatch: false, requestedTargetId: null }),
  false,
  'detail lookup must wait for the conflict list to settle',
);
assert.equal(
  shouldFetchConflictDetail({ targetId: '3', listLoading: false, hasListMatch: false, requestedTargetId: null }),
  true,
  'an explicit URL target may trigger one detail lookup after list loading',
);
assert.equal(
  shouldFetchConflictDetail({ targetId: '3', listLoading: false, hasListMatch: false, requestedTargetId: '3' }),
  false,
  'the same target must not trigger repeated detail requests',
);
assert.equal(
  shouldFetchConflictDetail({ targetId: null, listLoading: false, hasListMatch: false, requestedTargetId: null }),
  false,
  'normal page load must not fetch conflict detail',
);
assert.equal(
  shouldFetchConflictDetail({ targetId: '3', listLoading: false, hasListMatch: true, requestedTargetId: null }),
  false,
  'a conflict already present in the list must not trigger a detail request',
);
assert.equal(shouldRenderConflictListSkeleton(true), true);
assert.equal(shouldRenderConflictListSkeleton(false), false);
assert.equal(canRefreshConflictList(true), false, 'manual refresh must not overlap an active list request');
assert.equal(canRefreshConflictList(false), true);
assert.equal(getConflictListViewState(true, false, 0), 'LOADING');
assert.equal(getConflictListViewState(false, true, 0), 'ERROR', 'failed retrieval must not become empty state');
assert.equal(getConflictListViewState(false, false, 0), 'EMPTY');
assert.equal(getConflictListViewState(false, false, 1), 'RESULTS');

console.log('conflictFetchState acceptance tests passed');
