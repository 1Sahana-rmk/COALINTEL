import { apiClient } from './client';

export interface CitationItem {
  document_name: string;
  page_number: number;
  citation_tag: string;
  document_id?: number | null;
  evidence_type?: string | null;
  table_id?: number | null;
  locator?: Record<string, unknown>;
  source_url?: string | null;
  source_type?: string | null;
  file_type?: string | null;
  excerpt?: string | null;
  extraction_method?: string | null;
  confidence?: number | null;
  validation_state?: string | null;
}

export interface EvidenceChunkItem {
  chunk_id?: number | null;
  document_id: number;
  filename: string;
  page_number: number;
  chunk_index: number;
  text: string;
  rrf_score: number;
  vector_score?: number;
  keyword_score?: number;
  page_id?: number | null;
  table_id?: number | null;
  chunk_type?: string | null;
  source_locator?: Record<string, unknown>;
  source_url?: string | null;
  source_type?: string | null;
}

export interface QueryResponse {
  query: string;
  answer: string;
  citations: CitationItem[];
  evidence_chunks: EvidenceChunkItem[];
  provider: string;
  degraded_mode: boolean;
  mode?: string;
  route?: 'STRUCTURED' | 'SEMANTIC' | 'HYBRID' | string;
  support_state?: 'SUPPORTED' | 'CONFLICTING' | 'UNSUPPORTED' | 'UNAVAILABLE' | string;
  generation_status?: string;
  analysis?: Record<string, unknown>;
  structured_facts?: Array<Record<string, unknown>>;
  semantic_evidence?: Array<Record<string, unknown>>;
  conflicts?: Array<Array<Record<string, unknown>>>;
  source_references?: Array<Record<string, unknown>>;
}

export interface QueryRequestParams {
  top_k?: number;
  subsidiary_filter?: string;
}

export const queryApi = {
  askQuery: async (query: string, params?: QueryRequestParams): Promise<QueryResponse> => {
    const response = await apiClient.post<QueryResponse>('/query/ask', {
      query,
      top_k: params?.top_k ?? 5,
      subsidiary_filter:
        params?.subsidiary_filter &&
        params.subsidiary_filter !== 'ALL' &&
        params.subsidiary_filter !== 'ALL CIL'
          ? params.subsidiary_filter
          : null,
    });
    return response.data;
  },

  indexDocument: async (id: number): Promise<{ status: string; message: string }> => {
    const response = await apiClient.post<{ status: string; message: string }>(`/query/index-document/${id}`);
    return response.data;
  },
};
