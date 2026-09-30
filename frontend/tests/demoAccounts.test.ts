import assert from 'node:assert/strict';
import { DEMO_ACCOUNTS } from '@/lib/demoAccounts';

const expected = [
  ['admin', 'admin', 'Admin'],
  ['analyst', 'analyst', 'Analyst'],
  ['reviewer', 'reviewer', 'Reviewer'],
  ['viewer', 'auditor', 'Viewer'],
] as const;

for (const [shortcut, username, role] of expected) {
  const account = DEMO_ACCOUNTS[shortcut];
  assert.equal(account.username, username);
  assert.equal(account.role, role);
  assert.match(account.password, /.+/);
  assert.match(account.label, new RegExp(`${role} Login`));
}

assert.equal(Object.keys(DEMO_ACCOUNTS).length, 4);
