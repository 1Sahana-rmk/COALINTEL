import { apiClient } from './client';

export interface DocumentMetadataItem {
  id: string;
  document_title: string;
  organization: string;
  financial_year: string;
  document_type: string;
  publication_date: string;
  source_url: string | null;
  page_number: number | null;
  table_number: string | null;
  verification_status: string;
  is_active?: boolean;
}

export interface ComparisonSourceItem {
  metric_id: number | string;
  document_id: number | string;
  source_id?: string;
  document_title: string;
  filename: string;
  organization: string;
  document_type: string;
  subsidiary: string;
  mine_name: string;
  metric_name: string;
  original_metric_name: string;
  fiscal_year: string;
  period_type: string;
  data_status: string;
  as_of_date: string | null;
  raw_value: number;
  raw_unit: string;
  standard_value: number;
  standard_unit: string;
  page_number: number | null;
  table_number: string | null;
  source_url: string | null;
  publication_date: string | null;
  snippet: string;
  chunk_id: number | null;
  is_seeded_demo: boolean;
  provenance_label: string;
  verification_status: string;
}

export interface ConflictDetails {
  source_a: string;
  value_a: number;
  source_b: string;
  value_b: number;
  difference: number;
  difference_percent: number;
  possible_reason: string;
  status: string;
}

export interface ComparisonMatrixItem {
  entity: string;
  canonical_metric?: string;
  metric_name: string;
  fiscal_year: string;
  period_type?: string;
  as_of_date?: string | null;
  source_count: number;
  sources: ComparisonSourceItem[];
  units_compatible: boolean;
  variance_percentage: number;
  difference_value?: number;
  status: 'CONSISTENT' | 'DISCREPANCY DETECTED';
  has_discrepancy: boolean;
  is_seeded_demo: boolean;
  has_conflict?: boolean;
  canonical_conflict_id?: number | null;
  conflict_details?: ConflictDetails | null;
  provenance_notice: string;
}

export interface ComparisonConflictItem {
  conflict_id: number;
  entity: string;
  metric: string;
  financial_year: string;
  source_a: string;
  value_a: number;
  source_b: string;
  value_b: number;
  difference: number;
  difference_percent: number;
  possible_reason: string;
  status: string;
  resolved_value?: number | null;
  resolution_method?: string | null;
}

export interface ComparisonMatrixResponse {
  target_metric: string;
  target_domain: string;
  target_fiscal_year: string;
  subsidiary_scope: string;
  total_entities_compared: number;
  available_documents?: DocumentMetadataItem[];
  matrices: ComparisonMatrixItem[];
  conflicts?: ComparisonConflictItem[];
  summary_stats?: {
    total_entities: number;
    total_sources_evaluated: number;
    conflicts_count: number;
    consistent_count: number;
  };
}

export interface ComparisonOptionsResponse {
  subsidiaries: string[];
  entities: string[];
  metrics: string[];
  fiscal_years: string[];
  documents?: DocumentMetadataItem[];
}

export async function fetchComparisonOptions(): Promise<ComparisonOptionsResponse> {
  const response = await apiClient.get<ComparisonOptionsResponse>('/comparison/options');
  return response.data;
}

export async function fetchComparisonMatrix(params: {
  metric_name: string;
  fiscal_year?: string;
  entity_filter?: string;
  subsidiary_filter?: string;
  document_ids?: string[];
}): Promise<ComparisonMatrixResponse> {
  const queryParams = new URLSearchParams();
  queryParams.append('metric_name', params.metric_name);
  if (params.fiscal_year) queryParams.append('fiscal_year', params.fiscal_year);
  if (params.entity_filter) queryParams.append('entity_filter', params.entity_filter);
  if (params.subsidiary_filter) queryParams.append('subsidiary_filter', params.subsidiary_filter);
  if (params.document_ids && params.document_ids.length > 0) {
    params.document_ids.forEach((id) => queryParams.append('document_ids', id));
  }

  const response = await apiClient.get<ComparisonMatrixResponse>(`/comparison/matrix?${queryParams.toString()}`);
  return response.data;
}
