import { apiClient } from './client';

export interface CitationItem {
  document_name: string;
  page_number: number;
  citation_tag: string;
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
}

export interface QueryResponse {
  query: string;
  answer: string;
  citations: CitationItem[];
  evidence_chunks: EvidenceChunkItem[];
  provider: string;
  degraded_mode: boolean;
  mode?: string;
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
