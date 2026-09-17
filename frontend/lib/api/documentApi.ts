import { apiClient } from './client';
import {
  DocumentItem,
  DocumentListParams,
  DocumentListResponse,
  DocumentPagesResponse,
  DocumentLineageResponse,
} from '@/types/document';

export const documentApi = {
  uploadDocument: async (
    formData: FormData,
    onUploadProgress?: (progressEvent: { loaded: number; total?: number }) => void
  ): Promise<DocumentItem> => {
    const response = await apiClient.post<DocumentItem>('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (e) => {
        if (onUploadProgress) {
          onUploadProgress({ loaded: e.loaded, total: e.total });
        }
      },
    });
    return response.data;
  },

  getDocuments: async (params?: DocumentListParams): Promise<DocumentListResponse> => {
    const response = await apiClient.get<DocumentListResponse>('/documents', {
      params: {
        status_filter: params?.status_filter && params.status_filter !== 'ALL' ? params.status_filter : undefined,
        subsidiary_filter: params?.subsidiary_filter && params.subsidiary_filter !== 'ALL' && params.subsidiary_filter !== 'ALL CIL' ? params.subsidiary_filter : undefined,
        skip: params?.skip ?? 0,
        limit: params?.limit ?? 50,
      },
    });
    return response.data;
  },

  getDocumentById: async (id: number): Promise<DocumentItem> => {
    const response = await apiClient.get<DocumentItem>(`/documents/${id}`);
    return response.data;
  },

  getDocumentPages: async (id: number): Promise<DocumentPagesResponse> => {
    const response = await apiClient.get<DocumentPagesResponse>(`/documents/${id}/pages`);
    return response.data;
  },

  getDocumentLineage: async (id: number): Promise<DocumentLineageResponse> => {
    const response = await apiClient.get<DocumentLineageResponse>(`/documents/${id}/lineage`);
    return response.data;
  },

  deleteDocument: async (id: number): Promise<{ message: string; document_id: number; filename: string }> => {
    const response = await apiClient.delete<{ message: string; document_id: number; filename: string }>(`/documents/${id}`);
    return response.data;
  },
};

