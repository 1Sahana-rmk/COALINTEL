import { apiClient } from './client';

export interface ValidationItem {
  id: number;
  subsidiary: string;
  mine_name: string;
  metric_name: string;
  fiscal_year: string;
  reported_value: number | null;
  calculated_value?: number | null;
  standard_unit: string;
  percentage_difference: number | null;
  discrepancy_available: boolean;
  validation_status: string;
  message: string;
  document_id: number;
  filename: string;
  extraction_confidence?: number | null;
  page_number?: number | null;
  data_origin?: string | null;
}

export interface ConflictEvidence {
  document_id?: number | null;
  metric_id?: number | null;
  page_number?: number | null;
  bounding_box?: Record<string, number> | null;
  provenance_available: boolean;
  warning?: string | null;
}

export interface ConflictItem {
  id: number;
  conflict_key?: string;
  mine_name: string;
  subsidiary: string;
  metric_name: string;
  fiscal_year: string;
  document_a_id?: number | null;
  document_a_source_id?: string | null;
  document_a_filename: string;
  document_a_value: number;
  document_a_unit: string;
  evidence_a?: ConflictEvidence | null;
  document_b_id?: number | null;
  document_b_source_id?: string | null;
  document_b_filename: string;
  document_b_value: number;
  document_b_unit: string;
  evidence_b?: ConflictEvidence | null;
  discrepancy_percentage: number;
  status: string;
  resolved_by?: number | null;
  resolution_notes?: string | null;
  created_at?: string;
}

export interface ConflictListResponse {
  items: ConflictItem[];
  total: number;
  skip: number;
  limit: number;
  has_next: boolean;
}

export interface ResolveConflictPayload {
  resolution_action: string;
  override_value?: number;
  notes?: string;
}

export const validationApi = {
  getValidationFeed: async (subsidiary_filter?: string): Promise<ValidationItem[]> => {
    const response = await apiClient.get<ValidationItem[]>('/validation/feed', {
      params: {
        subsidiary_filter: subsidiary_filter && subsidiary_filter !== 'ALL' ? subsidiary_filter : undefined,
      },
    });
    return response.data;
  },

  getConflicts: async (
    status_filter?: string,
    subsidiary_filter?: string,
    signal?: AbortSignal,
    skip = 0,
    limit = 50,
  ): Promise<ConflictListResponse> => {
    const isSubAll =
      !subsidiary_filter ||
      subsidiary_filter.toUpperCase() === 'ALL' ||
      subsidiary_filter.toUpperCase() === 'ALL CIL' ||
      subsidiary_filter.toUpperCase() === 'ALL SUBSIDIARIES';

    const response = await apiClient.get<ConflictListResponse>('/conflicts', {
      signal,
      params: {
        status_filter: status_filter && status_filter !== 'ALL' ? status_filter : undefined,
        subsidiary_filter: isSubAll ? undefined : subsidiary_filter,
        skip,
        limit,
      },
    });
    return response.data;
  },

  getConflictById: async (id: number | string): Promise<ConflictItem> => {
    const response = await apiClient.get<ConflictItem>(`/conflicts/${id}`);
    return response.data;
  },

  resolveConflict: async (id: number | string, payload: ResolveConflictPayload): Promise<ConflictItem> => {
    const response = await apiClient.post<ConflictItem>(`/conflicts/${id}/resolve`, payload);
    return response.data;
  },
};
