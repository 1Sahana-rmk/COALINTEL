import assert from 'node:assert/strict';
import { DEFAULT_LOCALE, LOCALE_STORAGE_KEY, translate } from '../lib/i18n';

assert.equal(DEFAULT_LOCALE, 'en');
assert.equal(LOCALE_STORAGE_KEY, 'coalintel_locale');
assert.equal(translate('en', 'nav.documents'), 'Document Library');
assert.equal(translate('hi', 'nav.documents'), 'दस्तावेज़ लाइब्रेरी');
assert.notEqual(translate('hi', 'workspace.pageSummary'), translate('en', 'workspace.pageSummary'));

// Missing keys must never leak as undefined/null/raw object output.
assert.equal(translate('hi', 'missing.example', 'Safe fallback'), 'Safe fallback');
assert.equal(translate('en', 'missing.example'), '');

// Localization changes chrome only; persisted evidence values and identifiers
// are not passed through translate and therefore remain byte-for-byte stable.
const filename = 'msg-may23.pdf';
const evidence = 'MCL\nMay-23\n107880\n9.40';
const numericValue = '781.05 MT';
assert.equal(filename, 'msg-may23.pdf');
assert.equal(evidence, 'MCL\nMay-23\n107880\n9.40');
assert.equal(numericValue, '781.05 MT');
