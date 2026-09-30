import assert from 'node:assert/strict';
import {
  getOfficialSourceSyncError,
  isOfficialSourceSyncing,
  isTerminalOfficialSourceStatus,
} from '../lib/sourceSyncState';

const connected = { status: 'CONNECTED', last_error: null };
const syncing = { status: 'SYNCING', last_error: null };
const partial = { status: 'PARTIAL', last_error: 'one document failed' };

assert.equal(isOfficialSourceSyncing(connected), false, 'completed source must not show syncing');
assert.equal(isOfficialSourceSyncing(syncing), true, 'backend SYNCING status must drive the indicator');
assert.equal(isOfficialSourceSyncing(connected, true), true, 'accepted job remains tracked until a fresh terminal read');
assert.equal(isTerminalOfficialSourceStatus('SYNCING'), false);
assert.equal(isTerminalOfficialSourceStatus('CONNECTED'), true);
assert.equal(getOfficialSourceSyncError(partial), 'one document failed');
assert.equal(getOfficialSourceSyncError(connected), null);

// Reload semantics: persisted SYNCING is enough to resume polling, while a
// persisted terminal result must not recreate a local syncing flag.
assert.equal(isOfficialSourceSyncing(syncing, false), true);
assert.equal(isOfficialSourceSyncing(connected, false), false);

console.log('sourceSyncState acceptance tests passed');
