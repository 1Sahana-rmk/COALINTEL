import assert from 'node:assert/strict';
import {
  ALL_FISCAL_YEARS_VALUE,
  authoritativeCatalogDocuments,
  canRequestComparisonMatrix,
  canonicalDocumentIds,
  comparisonRequestKey,
  shouldApplyComparisonResponse,
} from '../lib/comparisonState';
import { DocumentMetadataItem } from '../lib/api/comparisonApi';
import { buildComparisonMatrixQuery } from '../lib/api/comparisonApi';

const metadata = (id: string, title: string, kind: 'catalog' | 'ingested'): DocumentMetadataItem => ({
  id,
  document_title: title,
  document_kind: kind,
  organization: 'Test organization',
  financial_year: '2024-25',
  document_type: 'PDF',
  publication_date: '2026-01-01',
  source_url: null,
  page_number: null,
  table_number: null,
  verification_status: 'verified',
});

const catalog = [
  metadata('MOC-CD-2024-25', 'Coal Despatch', 'catalog'),
  metadata('MOC-AR-2024-25', 'Annual Report', 'catalog'),
  metadata('161', 'Uploaded PDF', 'ingested'),
];

assert.deepEqual(
  authoritativeCatalogDocuments(catalog).map((document) => document.id),
  ['MOC-CD-2024-25', 'MOC-AR-2024-25'],
  'catalog selection must not append numeric ingested document IDs',
);
assert.deepEqual(canonicalDocumentIds(['MOC-AR-2024-25', 'MOC-CD-2024-25', 'MOC-AR-2024-25']), [
  'MOC-AR-2024-25',
  'MOC-CD-2024-25',
]);

const currentKey = comparisonRequestKey({
  metricName: 'Coal Production',
  fiscalYear: '2024-25',
  entityFilter: '',
  subsidiaryFilter: 'ALL CIL',
  documentIds: ['MOC-CD-2024-25', 'MOC-AR-2024-25'],
});
const sameSelectionDifferentOrder = comparisonRequestKey({
  metricName: 'Coal Production',
  fiscalYear: '2024-25',
  entityFilter: '',
  subsidiaryFilter: 'ALL CIL',
  documentIds: ['MOC-AR-2024-25', 'MOC-CD-2024-25'],
});
assert.equal(currentKey, sameSelectionDifferentOrder, 'request identity must be order-independent');
assert.equal(canRequestComparisonMatrix(false, ['MOC-CD-2024-25']), false);
assert.equal(canRequestComparisonMatrix(true, []), false, 'empty transient selection must not mean all documents');
assert.equal(canRequestComparisonMatrix(true, ['MOC-CD-2024-25']), true);

const outgoingQuery = new URLSearchParams(buildComparisonMatrixQuery({
  metric_name: 'Coal Production',
  fiscal_year: '2024-25',
  subsidiary_filter: 'ALL CIL',
  document_ids: ['MOC-CD-2024-25', 'MOC-AR-2024-25'],
}));
assert.deepEqual(outgoingQuery.getAll('document_ids'), ['MOC-AR-2024-25', 'MOC-CD-2024-25']);
assert.equal(outgoingQuery.getAll('document_ids').some((id) => /^\d+$/.test(id)), false);

assert.equal(ALL_FISCAL_YEARS_VALUE, '', 'All Fiscal Years must use the empty API filter value');
const unfilteredQuery = new URLSearchParams(buildComparisonMatrixQuery({
  metric_name: 'Coal Production',
  fiscal_year: ALL_FISCAL_YEARS_VALUE,
  subsidiary_filter: 'ALL CIL',
  document_ids: ['MOC-CD-2024-25', 'MOC-AR-2024-25'],
}));
assert.equal(
  unfilteredQuery.has('fiscal_year'),
  false,
  'the initial All Fiscal Years request must omit the fiscal_year restriction',
);

assert.equal(shouldApplyComparisonResponse(currentKey, currentKey, 2, 2), true);
assert.equal(
  shouldApplyComparisonResponse(currentKey, currentKey, 1, 2),
  false,
  'delayed obsolete response must not replace current matrix',
);
assert.equal(
  shouldApplyComparisonResponse('{"document_ids":[]}', currentKey, 2, 2),
  false,
  'empty-selection response must not replace explicit selection',
);

console.log('comparisonState acceptance tests passed');
