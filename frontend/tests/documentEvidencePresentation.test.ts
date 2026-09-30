import assert from 'node:assert/strict';
import { buildPageContentSummary, displayPersistedTableValue, hasReliableStructuredTable, metricForEvidence, persistedTableMerges, structuredRows, tableColumnCount, tablesForPage } from '../lib/documentEvidencePresentation';

const table = {
  id: 1,
  page_number: 4,
  table_number: 1,
  title: 'Production',
  headers: ['Mine', 'April', 'May'],
  rows: [['A', 781.05, ''], ['B', null, 12.5]],
  bounding_box: [1, 2, 3, 4],
  extraction_confidence: 0.9,
  extraction_method: 'NATIVE_TABLE',
  sheet_name: null,
  cells: [],
  warnings: [],
};

assert.equal(tablesForPage([table], 4).length, 1);
assert.equal(tablesForPage([table], 5).length, 0);
assert.deepEqual(structuredRows(table), table.rows);
assert.equal(tableColumnCount(table), 3);
assert.equal(hasReliableStructuredTable(table), true);
assert.deepEqual(persistedTableMerges({ ...table, merged_cells: ['A1:B1', 'C2:C3'] }), [
  { startRow: 1, startColumn: 1, endRow: 1, endColumn: 2 },
  { startRow: 2, startColumn: 3, endRow: 3, endColumn: 3 },
]);
assert.deepEqual(persistedTableMerges(table), [], 'absence of merge metadata must remain absence of spans');
assert.equal(buildPageContentSummary([table]), 'This page contains “Production” table. It contains 2 data rows with columns for Mine, April, May.');
assert.deepEqual(structuredRows(table)[0], ['A', 781.05, ''], 'blank trailing cells must remain blank');
assert.equal(structuredRows(table)[1][1], null, 'blank numeric cells must remain blank');
const blankHeaderTable = {
  ...table,
  headers: ["Top 35 Mines Production during May'2023 (provisional)", '', null],
  rows: [['BCCL', 781.05, '']],
};
assert.equal(tableColumnCount(blankHeaderTable), 3, 'blank headers must retain their grid columns');
assert.equal(blankHeaderTable.headers.length, 3, 'blank headers must remain present in the persisted header grid');
assert.equal(displayPersistedTableValue(blankHeaderTable.headers[1]), '', 'blank header cells render no placeholder text');
assert.equal(displayPersistedTableValue(blankHeaderTable.headers[2]), '', 'null header cells render no placeholder text');
assert.equal(displayPersistedTableValue(blankHeaderTable.rows[0][2]), '', 'blank body cells render no placeholder text');
assert.equal(displayPersistedTableValue('781.05'), '781.05', 'non-blank table values remain unchanged');
assert.equal(displayPersistedTableValue('Blank header'), 'Blank header', 'stored literal values remain unchanged');
assert.equal(structuredRows({ ...table, rows: [] }).length, 0, 'missing structure must not be reconstructed');
assert.equal(hasReliableStructuredTable({ ...table, headers: [], rows: [], cells: [] }), false);
assert.equal(buildPageContentSummary([]), '', 'ordinary text pages must keep the existing text-first presentation');
assert.equal(
  metricForEvidence([{
    id: 7001,
    mine_name: 'MCL',
    metric_name: 'Coal Production',
    numeric_value: 781.05,
    unit: 'MT',
    standard_value: 781.05,
    standard_unit: 'MT',
    fiscal_year: '2023-24',
    validation_status: 'VALIDATED',
    raw_snippet: '781.05 MT',
    page_number: 4,
  }], '7001')?.page_number,
  4,
);
assert.equal(metricForEvidence([], '7001'), null);

console.log('document evidence presentation acceptance tests passed');
