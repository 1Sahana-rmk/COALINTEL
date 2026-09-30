import assert from 'node:assert/strict';
import { dashboardKpiSubtitle } from '../lib/dashboardKpiPresentation';

assert.equal(
  dashboardKpiSubtitle('728.40', 'FY 2025-26', true, 'Production Scope Total', 'No data available'),
  'FY 2025-26',
);
assert.equal(
  dashboardKpiSubtitle('712.30', 'FY 2026-27 (YTD Provisional)', true, 'Production Scope Total', 'No data available'),
  'FY 2026-27 (YTD Provisional)',
);
assert.equal(
  dashboardKpiSubtitle('N/A', null, true, 'Production Scope Total', 'No data available'),
  'No data available',
);
assert.equal(
  dashboardKpiSubtitle('20.00', 'FY 2023-24', true, 'Production Scope Total', 'No data available'),
  'FY 2023-24',
);
