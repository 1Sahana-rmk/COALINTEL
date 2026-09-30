import { DocumentMetadataItem } from './api/comparisonApi';

/** Empty is the API-level representation of the unfiltered selector option. */
export const ALL_FISCAL_YEARS_VALUE = '';

export interface ComparisonRequestState {
  metricName: string;
  fiscalYear: string;
  entityFilter: string;
  subsidiaryFilter: string;
  documentIds: string[];
}

/** Keep selection identity deterministic; ordering is not comparison semantics. */
export function canonicalDocumentIds(documentIds: string[]): string[] {
  return [...new Set(documentIds)].sort();
}

export function comparisonRequestKey(state: ComparisonRequestState): string {
  return JSON.stringify({
    metric_name: state.metricName,
    fiscal_year: state.fiscalYear,
    entity_filter: state.entityFilter || '',
    subsidiary_filter: state.subsidiaryFilter || '',
    document_ids: canonicalDocumentIds(state.documentIds),
  });
}

/**
 * The comparison selector is an authoritative catalog selector. Ingested
 * database documents remain valid API identifiers, but are not silently mixed
 * into this catalog's selection state.
 */
export function authoritativeCatalogDocuments(documents: DocumentMetadataItem[]): DocumentMetadataItem[] {
  const hasExplicitKinds = documents.some((document) => document.document_kind !== undefined);
  if (hasExplicitKinds) {
    return documents.filter((document) => document.document_kind === 'catalog');
  }

  // Compatibility with an older backend response during rolling deployment:
  // catalog source IDs are non-numeric, while database document IDs are numeric.
  return documents.filter((document) => !/^\d+$/.test(document.id));
}

export function canRequestComparisonMatrix(optionsReady: boolean, documentIds: string[]): boolean {
  // The backend treats omitted document_ids as "all documents". Never turn a
  // transient or explicit empty selection into that broader query.
  return optionsReady && canonicalDocumentIds(documentIds).length > 0;
}

export function shouldApplyComparisonResponse(
  responseRequestKey: string,
  currentRequestKey: string,
  responseRequestId: number,
  currentRequestId: number,
): boolean {
  return responseRequestKey === currentRequestKey && responseRequestId === currentRequestId;
}
