import assert from 'node:assert/strict';
import { ALL_FISCAL_YEARS_VALUE, FISCAL_YEARS } from '../lib/constants';
import { normalizeDashboardFiscalYear } from '../lib/api/dashboardApi';

assert.equal(FISCAL_YEARS[0].value, ALL_FISCAL_YEARS_VALUE);
assert.equal(FISCAL_YEARS[0].label, 'All Fiscal Years');
assert.equal(ALL_FISCAL_YEARS_VALUE, 'ALL');

// The dashboard sends no fiscal-year restriction for the explicit all-years
// state, while specific years remain unchanged.
assert.equal(normalizeDashboardFiscalYear(ALL_FISCAL_YEARS_VALUE), undefined);
assert.equal(normalizeDashboardFiscalYear('2022-23'), '2022-23');
assert.equal(normalizeDashboardFiscalYear(undefined), undefined);

console.log('dashboard fiscal-year acceptance tests passed');
