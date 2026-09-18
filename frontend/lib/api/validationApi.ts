import { apiClient } from './client';

export interface ValidationItem {
  id: number;
  subsidiary: string;
  mine_name: string;
  metric_name: string;
  discrepancy: string;
  details: string;
  status: string;
  confidence: number;
  page_number?: number;
  document_name?: string;
  created_at?: string;
}

export interface ConflictItem {
  id: number;
  mine_name: string;
  subsidiary: string;
  metric_name: string;
  fiscal_year: string;
  document_a_id: number;
  document_a_filename: string;
  document_a_value: number;
  document_a_unit: string;
  document_b_id: number;
  document_b_filename: string;
  document_b_value: number;
  document_b_unit: string;
  discrepancy_percentage: number;
  status: string;
  resolved_by?: number | null;
  resolution_notes?: string | null;
  created_at?: string;
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

  getConflicts: async (status_filter?: string, subsidiary_filter?: string): Promise<ConflictItem[]> => {
    const isSubAll =
      !subsidiary_filter ||
      subsidiary_filter.toUpperCase() === 'ALL' ||
      subsidiary_filter.toUpperCase() === 'ALL CIL' ||
      subsidiary_filter.toUpperCase() === 'ALL SUBSIDIARIES';

    const response = await apiClient.get<ConflictItem[]>('/conflicts', {
      params: {
        status_filter: status_filter && status_filter !== 'ALL' ? status_filter : undefined,
        subsidiary_filter: isSubAll ? undefined : subsidiary_filter,
      },
    });
    return response.data;
  },

  getConflictById: async (id: number | string): Promise<ConflictItem> => {
    const response = await apiClient.get<ConflictItem>(`/conflicts/${id}`);
    return response.data;
  },

  resolveConflict: async (id: number, payload: ResolveConflictPayload): Promise<ConflictItem> => {
    const response = await apiClient.post<ConflictItem>(`/conflicts/${id}/resolve`, payload);
    return response.data;
  },
};
